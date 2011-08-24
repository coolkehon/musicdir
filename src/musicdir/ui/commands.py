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

import logging
import codecs

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
            if path:
                print_(rls.dirpath)
            else:
                aname = rls.artist.name if rls.artist != None else 'Unknown Artist'
                print_(aname + u' - ' + rls.name)
    else:
        for track in lib.tracks(fields):
            if path and track.file != None:
                print_(track.file.path)
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
            are = re.compile(r'\.(nfo|cue|log)$', re.I)
            cover_re = re.compile(r'(folder|cover|cd|front)\.(jpg|jpeg|png|bmp)$', re.I)

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
                    mfiles.append(file)
                elif opts.attachments == True and cover == None and cover_re.search(file):
                    if opts.verbose:
                        print_(file)
                    cover = File(path=file)
                elif opts.attachments == True and are.search(file):
                    if opts.verbose:
                        print_(file)
                    afiles.append(file)

            if len(mfiles) > 0:
                attachments = [ ]
                for file in afiles:
                    attachments.append(Attachment(file=File(path=file), name=file.decode('utf8','replace')) )

                if cover != None:
                    attachments.append(Attachment(file=cover, name='cover'))

                for file in  mfiles:
                    try:
                        track = Track()
                        track.read(file)

                        if opts.attachments == True:
                            track.attachments = attachments
                            if track.release != None:
                                track.release.cover = cover

                        if opts.checksum == True:
                            if track.file is not None:
                                track.file.checksum()
                            for atch in track.attachments:
                                atch.file.checksum()

                        lib.session.add(track)
                    except UnreadableFileError:
                        logger.error(u'FAILED: ' + file.decode('utf8', 'replace'))
                        if logfile != None:
                            logfile.write(file.decode('utf8', 'replace') + u'\n')
            
    if logfile != None:
        logfile.close()
    lib.session.commit()

import_cmd.func = import_func
default_commands.append(import_cmd)
# }}}
