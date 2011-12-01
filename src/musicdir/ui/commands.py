# This file is part of musicdir.
# Copyright 2011, coolkehon.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

from musicdir import ui
from musicdir.ui import print_
from musicdir.util import *
from musicdir.library import *
from musicdir.mediafile import UnreadableFileError
from musicdir import importer

import logging
import codecs

from sqlalchemy import func

# The list of default subcommands. This is populated with Subcommand
# objects that can be fed to a SubcommandsOptionParser.
default_commands = []

# {{{ list: Query and show library contents.
def list_items(lib, query, release, path):
    """Print out items in lib matching query. If album, then search for
    albums instead of single items. If path, print the matched objects'
    paths instead of human-readable information about them.
    """
    fields = [ ]
    if isinstance(query, list):
        fields = [ q.decode('utf8', 'replace') for q in query ]
    elif query != None:
        fields = [ query.decode('utf8', 'replace') ]
    
    if release:
        for rls in lib.releases(fields):
            aname = rls.artist.name if rls.artist != None else 'Unknown Artist'
            print_(aname + u' - ' + rls.name)
    else:
        for track in lib.tracks(fields):
            if path:
                if track.files is not None:
                    for trackfile in track.files:
                        print_(trackfile.file.path)
            else:
                aname = track.artist.name if track.artist != None else 'Unknown Artist'
                rname = track.release.name if track.release != None else 'Unknown Release'
                print_(aname + u' - ' + rname + u' - ' + track.title)

list_cmd = ui.Subcommand('list', help='query the library', aliases=('ls',))
list_cmd.parser.add_option('-r', '--release', action='store_true',
    help='show matching releases instead of tracks')
list_cmd.parser.add_option('-p', '--path', action='store_true',
    help='print paths for matched items or albums')
def list_func(lib, config, opts, args):
    list_items(lib, args, opts.release, opts.path)
list_cmd.func = list_func
default_commands.append(list_cmd)
# }}} end list: Query and show library contents

# {{{ stats: Query and show library stats
stats_cmd = ui.Subcommand('stats', help='show library stats')
def stats_func(lib, config, opts, args):
    total_size = lib.session.query(func.sum(File.size)).scalar()
    if total_size is None:
        total_size = 0
    total_time = lib.session.query(func.sum(Track.length)).scalar()
    if total_time is None:
        total_time = 0
    total_tracks = lib.session.query(func.count(Track.id)).scalar()
    if total_tracks is None:
        total_tracks = 0
    total_artists = lib.session.query(func.count(Artist.id)).scalar()
    if total_artists is None:
        total_artists = 0
    total_releases = lib.session.query(func.count(Release.id)).scalar()
    if total_releases is None:
        total_releases = 0
    total_files = lib.session.query(func.count(File.id)).scalar()
    if total_files is None:
        total_files = 0

    print_("Size: %s\nTime: %s\nTracks: %i\nArtists: %i\nReleases: %i\nFiles: %i" %
            ( ui.human_bytes(float(total_size))
            , ui.human_seconds(float(total_time))
            , total_tracks
            , total_artists
            , total_releases
            , total_files) )

stats_cmd.func = stats_func
default_commands.append(stats_cmd)
# }}} end stats: Query and show library stats

# {{{ import: simple import into library
import_cmd = ui.Subcommand('import', help='import new music',
    aliases=('imp', 'im'))
import_cmd.parser.add_option('-v', '--verbose', action='store_true',
    help='turn up the verbosity level!!!')
import_cmd.parser.add_option('-l', '--log', dest='logpath',
    help='file to log untaggable albums for later review')
import_cmd.parser.add_option('-a', '--attachments', action='store_true',
    help='attach files in same directory as audio files')
import_cmd.parser.add_option('-c', '--checksum', action='store_true',
    help='add checksum to new files. NOTE: this will take awhile')
#import_cmd.parser.add_option('', '', action='store_false',
#    help='')

def import_func(lib, config, opts, args):
    logger = logging.getLogger('importer')
    if opts.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    logfile = None
    if opts.logpath:
        logfile = codecs.open(opts.logpath, 'w', 'utf-8')

    for topdir in args:
        topdir = bytestring_path(topdir)
        for root, dirs, files in sorted_walk(topdir):
            lib.session.commit()
            # logger.info(root)
            print_(root)

            mre = re.compile(r'\.(m4a|mp4|mp3|flac|ogg|ape|wv|mpc)$', re.I)
            are = re.compile(r'\.(nfo|cue|log|xml)$', re.I)
            cover_re = re.compile(r'(folder|cover|cd|front)\.(jpg|jpeg|png|bmp|tiff|svg)$', re.I)

            mfiles = [ ] # audio files
            afiles = [ ] # attachments
            cover = None

            for file in files:
                file = os.path.join(root, file)

                # skip duplicates for now
                if lib.session.query(File.path).filter(File.path == file).count() > 0:
                    continue

                if mre.search(file):
                    if opts.verbose:
                        print_(file)
                    mfiles.append(File(path=syspath(file), size=os.path.getsize(syspath(file))) )

                elif opts.attachments == True and cover == None and cover_re.search(file):
                    if opts.verbose:
                        print_(file)
                    cover = Attachment(file=File(path=file), name=u'cover')
                    afiles.append(cover)

                elif opts.attachments == True and are.search(file):
                    if opts.verbose:
                        print_(file)
                    afiles.append(Attachment(file=File(path=file), name=file.decode('utf8','replace')) )

            if len(mfiles) > 0:
                tracks = [ ]
                for mfile in mfiles:
                    try:
                        track = importer.import_track( \
                                lib=lib, \
                                file=mfile, \
                                attachments=afiles, \
                                cover=cover )
                        tracks.append(track)
                    except UnreadableFileError:
                        if logfile != None:
                            logfile.write(u'FAILED: ' + mfile.path.decode('utf8', 'replace') + u'\n')

                # do checksum
                if opts.checksum == True:
                    for file in  mfiles:
                        if opts.checksum == True:
                            if file is not None:
                                file.checksum()

                            for atch in afiles:
                                atch.file.checksum()

                for track in tracks:
                    lib.session.add(track)
                
    if logfile != None:
        logfile.close()
    lib.session.commit()

import_cmd.func = import_func
default_commands.append(import_cmd)
# }}}
