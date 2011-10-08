import os, sys
import codecs

from musicdir.ui import print_
from musicdir.util import *
from musicdir.library import *
from musicdir.mediafile import UnreadableFileError

def import_tracks(lib=None, files=[ ], attachments=[ ], cover=None):
    return [ import_track(lib=lib, file=file, attachments=attachments, cover=cover) for file in files ]
    
def import_track(lib=None, file=None, attachments=[ ], cover=None):
    if os.path.exists(file.path):
        session = lib.session

        # get trackfile if it exists
        trackfile = session.query(TrackFile).filter(File.id == file.id).first()
        if trackfile is not None \
            and trackfile.track is not None:
            return trackfile

        # read metadata in
        f = MediaFile(file.path)

        # get / create artist
        artist = None
        if f.artist != None and len(f.artist) > 0:
            artist = session.query(Artist).filter(Artist.name == f.artist).first()
            if artist is None:
                artist = Artist(name=f.artist)

        # album artist shall suffice if artist is not defined
        elif f.albumartist != None and len(f.albumartist) > 0:
            artist = session.query(Artist).filter(Artist.name == f.albumartist).first()
            if artist is None:
                artist = Artist(name=f.albumartist)
        
        # get / create release
        release = None
        if f.album != None and len(f.album) > 0:
            query = session.query(Release)\
                    .outerjoin(Artist, Artist.id == Release.artist_id)

            # start filter
            filter = Release.name == f.album

            # check if compilation
            if f.comp is not None:
                filter = and_(filter, Release.compilation == f.comp)

            # get album artist
            if not f.comp and f.albumartist != None and len(f.albumartist) > 0:
                filter = and_(filter, Artist.name == f.albumartist)

            release = query.filter(filter).first()
            if release == None:
                release = Release(name=f.album, tracktotal=f.tracktotal, disctotal=f.disctotal, compilation=f.comp)
                
                if f.albumartist != None and len(f.albumartist) > 0:
                    release.artist = session.query(Artist).filter(Artist.name == f.albumartist).first()
                    if release.artist is None:
                        release.artist = Artist(name=f.albumartist)

        # get / create track
        track = None
        if f.title != None:
            query = session.query(Track)\
                    .outerjoin(Artist, Artist.id == Track.artist_id)\
                    .outerjoin(Release, Release.id == Track.release_id)\


            filter = Track.title == f.title
            if artist is not None:
                filter = and_(filter, Artist.id == artist.id)
            else:
                filter = and_(filter, Artist.id == None)

            if release is not None:
                filter = and_(filter, Release.id == release.id)
            else:
                filter = and_(filter, Release.id == None)

            track = query.filter(filter).first()

        if track is None:
            track = Track(
                    artist=artist,
                    release=release,
                    title=f.title,
                    genre=f.genre,
                    track=f.track,
                    disc=f.disc,
                    length=f.length,
                    bpm=f.bpm,
                    composer=f.composer,
                    date=f.date )
        
        # create trackfile 
        if trackfile is None:
            trackfile = TrackFile(
                    file=file, 
                    track=track, 
                    bitrate=f.bitrate, 
                    format=f.format, 
                    attachments=attachments, 
                    cover=cover )
            # add to session
            lib.session.add(trackfile)

        return trackfile


