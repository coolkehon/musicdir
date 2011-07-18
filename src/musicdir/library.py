# This file is part of musicdir.
# Copyright 2011, coolkehon
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

# {{{ imports
import os
import re
import sys
import time, datetime
from string import Template

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.exc import NoResultFound

from musicdir.util import bytestring_path, syspath
from musicdir.mediafile import MediaFile
# }}} end imports

metadata = MetaData()
Session = scoped_session(sessionmaker())
Base = declarative_base(metadata=metadata)

# {{{ File(Base)
class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    path = Column(BLOB)
    size = Column(Integer)
    dateadded = Column(DateTime)
    presum = Column(UnicodeText)

    def __init__(self, path=None, size=None, dateadded=None, presum=None):
        self.path = path
        self.size = size
        self.dateadded = dateadded
        self.presum = presum

    def exists():
        return self.path != None and os.path.exists(self.path)
# }}} end File(Base)

# {{{ Attachment(Base)
class Attachment(Base):
    __tablename__ = 'attachments'

    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText)
    description = Column(UnicodeText)
    file_id = Column(Integer, ForeignKey(File.id))

    file = relationship(File, primaryjoin=file_id == File.id)

    def __init__(self, file=None, name=None, description=None):
        self.file = file
        self.name = name
        self.description = description
# }}} end Attachment(Base)

# {{{ Associative Tables
track_attachments = Table('track_attachments', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('track_id', Integer, ForeignKey('tracks.id')) ,
        Column('attachment_id', Integer, ForeignKey(Attachment.id)) )

release_attachments = Table('release_attachments', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('release_id', Integer, ForeignKey('releases.id')),
        Column('attachment_id', Integer, ForeignKey(Attachment.id)) )

artist_attachments = Table('artist_attachments', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('artist_id', Integer, ForeignKey('artists.id')),
        Column('attachment_id', Integer, ForeignKey(Attachment.id)) )

# }}} end Associative Tables

# {{{ Artist(Base)
class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText)
    description = Column(UnicodeText)
    artfile_id = Column(Integer, ForeignKey(File.id))

    art = relationship(File, primaryjoin=artfile_id == File.id, uselist=False)
    attachments = relationship(Attachment, secondary=artist_attachments)

    def __init__(self, name=None, description=None, artpath=None):
        self.name = name
        self.description = description
        self.artpath = artpath
# }}} end Artist(Base)

# {{{ Release(Base)
class Release(Base):
    __tablename__ = 'releases'

    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText)
    type = Column(UnicodeText)
    coverfile_id = Column(Integer, ForeignKey(File.id))
    artist_id = Column(Integer, ForeignKey(Artist.id))
    date = Column(Date)
    tracktotal = Column(Integer)
    disctotal = Column(Integer)
    compilation = Column(Boolean)
    dirpath = Column(UnicodeText)

    cover = relationship(File, primaryjoin=coverfile_id == File.id, uselist=False)
    artist = relationship(Artist, primaryjoin=artist_id == Artist.id, backref='releases')
    attachments = relationship(Attachment, secondary=release_attachments)

    def __init__(self, name=None, type=None, artpath=None, artist=None, date=None, tracktotal=None, disctotal=None, compilation=None, dirpath=None):
        self.name = name
        self.type = type
        self.artpath = artpath
        self.artist = artist
        self.date = date
        self.tracktotal = tracktotal
        self.disctotal = disctotal
        self.compilation = compilation
        self.dirpath = dirpath
# }}} end Release(Base)

# {{{ Track(Base)
class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey(Artist.id))
    release_id = Column(Integer, ForeignKey(Release.id))
    file_id = Column(Integer, ForeignKey(File.id))
    title = Column(UnicodeText)
    track = Column(Integer)
    discnum = Column(Integer)
    genre = Column(UnicodeText)
    date = Column(Date)
    composer = Column(UnicodeText)
    lyrics = Column(UnicodeText)
    comments = Column(UnicodeText)
    bitrate = Column(Integer)
    format = Column(UnicodeText)
    length = Column(Integer)
    bpm = Column(Integer)

    artist = relationship(Artist, primaryjoin=artist_id == Artist.id, backref='tracks')
    release = relationship(Release, primaryjoin=release_id == Release.id, backref='tracks')
    file = relationship(File, primaryjoin=file_id == File.id)
    attachments = relationship(Attachment, secondary=track_attachments)

    def __init__(self, artist=None, release=None, file=None, title=None, track=None, discnum=None, genre=None, date=None, composer=None, lyrics=None, comments=None, bitrate=None, format=None, length=None, bpm=None):
        self.artist = artist
        self.release = release
        self.file = file
        self.title = title
        self.track = track
        self.discnum = discnum
        self.genre = genre
        self.date = date
        self.composer = composer
        self.lyrics = lyrics
        self.comments = comments
        self.bitrate = bitrate
        self.format = format
        self.length = length

    # {{{ read(self, filepath)
    def read(self, filepath):
        """Read the track's metdata from filepath
        """
        session = Session()
        if os.path.exists(filepath):
            self.file = File(path=syspath(filepath))
            
            f = MediaFile(self.file.path)
            self.title = f.title

            if f.artist != None and len(f.artist) > 0:
                self.artist = session.query(Artist).filter(Artist.name == f.artist).first()
                if self.artist == None:
                    self.artist = Artist(name=f.artist)

            elif f.albumartist != None and len(f.albumartist) > 0:
                self.artist = session.query(Artist).filter(Artist.name == f.albumartist).first()
                if self.artist == None:
                    self.artist = Artist(name=f.albumartist)
            
            if f.album != None and len(f.album) > 0:
                query = session.query(Release).filter(Release.name == f.album)
                if f.albumartist != None and len(f.albumartist) > 0:
                    query = query.filter(Artist.name == f.albumartist)

                elif self.artist != None:
                    query = query.filter(Artist.name == self.artist.name)
                
                self.release = query.first()
                if self.release == None:
                    self.release = Release(name=f.album, tracktotal=f.tracktotal, disctotal=f.disctotal, compilation=f.comp)
                    
                    if self.artist != None and f.albumartist != None and self.artist.name == f.albumartist:
                        self.release.artist = self.artist

                    elif f.albumartist != None and len(f.albumartist) > 0:
                        self.release.artist = session.query(Artist).filter(Artist.name == f.albumartist).first()
                        if self.release.artist == None:
                            self.release.artist = Artist(name=f.albumartist)

                    elif self.artist != None:
                        self.release.artist = self.artist
             
            self.genre = f.genre
            self.composer = f.composer
            self.track = f.track
            self.discnum = f.disc
            self.lyrics = f.lyrics
            self.comments = f.comments
            self.bpm = f.bpm
            self.length = f.length
            self.bitrate = f.bitrate
            self.format = f.format
    # }}} end read(self, filepath)

    # {{{ write(self)
    def write(self):
        """Write the track's metadata to the associated file.
        """
        #f = MediaFile(syspath(self.filepath))
        # TODO save values to mediafile
        #f.title = self.title
        #f.artist = self.lib.artist(self.artist).name
        #f.album = self.lib.release(self.release).name
        #f.genre = self.genre
        #f.composer = self.composer
        # f.grouping = 

        # parse time format
        # TODO add these to beets.util
        #time_format = "%Y-%m-%d %H:%M:%S"
        #date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(self.date, time_format)))
        #f.year = date.year
        #f.month = date.month
        #f.day = date.day
        #f.date = self.date
        #f.track = self.track
        #f.tracktotal = self.lib.release(self.release).tracktotal
        #f.disc = self.disc
        #f.disctotal = self.lib.release(self.release).disctotal
        # f.lyrics = 
        #f.comments = 
        #f.bpm = 
        #f.comp = 
        #f.albumartist = 
        #f.albumtype =
        # f.art = 
        #f.mb_trackid = 
        #f.mb_albumid = 
        #f.mb_artistid = 
        #f.mb_albumartistid = 
        #f.save()
    # }}} end write(self)
# }}} end Track(Item)

# {{{ BaseLibrary
class BaseLibrary(object):
    """Abstract BaseLibrary class for music libraries"""
    def __init__(self):
        raise NotImplemented

    def add(self, item):
        """Add a Item (track, release, artist, etc) to the database"""
        raise NotImplemented

    # Basic functions
    def releases(self, query=None):
        """Should return a list of releases in database matching query.
        If query is None then return all releases
        """
        raise NotImplemented

    def release(self, release_id):
        """Should return one release identified by release_id"""
        raise NotImplemented

    def artists(self, query=None):
        """Similar to releases() but for artist"""
        raise NotImplemented

    def artist(self, artist_id):
        """Should return one artist identified by artist_id"""
        raise NotImplemented

    def tracks(self, query=None):
        """Similar to releases() but for tracks"""
        raise NotImplemented

    def track(self, track_id):
        """Should return on track identifed by track_id"""
        raise NotImplemented
        
# }}} end BaseLibrary

# {{{ Library(BaseLibrary)
class Library(BaseLibrary):
    """A Music Library using an SQLite database as the metadata store."""
    # {{{ __init__(self, path, directory, path_format, art_filename)
    def __init__(self, dburi='sqlite:///musicdir.db',
                       directory='~/Music',
                       path_formats=None,
                       art_filename='cover'):
        self.directory = bytestring_path(directory)
        if path_formats is None:
            path_formats = {'default': '$artist/$album/$track $title'}
        elif isinstance(path_formats, basestring):
            path_formats = {'default': path_formats}
        self.path_formats = path_formats
        self.art_filename = bytestring_path(art_filename)

        # setup database connections
        self.db = create_engine(dburi)
        self.db.echo = False
        Session.configure(bind=self.db)
        self.session = Session()
 

        # make sure that the database tables are created
        metadata.create_all(self.db)

    # }}} end __init__(self, path, directory, path_format, art_filename)

    # {{{ get_filter(self, field)
    def get_filter(self, field):
        """Transform a field into a filter using python regex
        """
        # like matches
        m = re.match(r'^(.*?):(.*?)$', field)
        if m != None:
            if re.match(r'^(album|release)$', m.group(1), re.I):
                return Release.name.like('%' + m.group(2) + '%')
            elif re.match(r'^artist$', m.group(1), re.I):
                return Artist.name.like('%' + m.group(2) + '%')
            elif re.match(r'^(title|track)$', m.group(1), re.I):
                return Track.title.like('%' + m.group(2) + '%')
            elif re.match(r'^path$', m.group(1), re.I):
                return or_(Release.dirpath.like('%' + m.group(2) + '%'), File.path.like('%' + m.group(2) + '%') )

        # exact matches
        m = re.match(r'^(.*?)=(.*?)$', field)
        if m != None:
            if re.match(r'^(album|release)$', m.group(1), re.I):
                return Release.name == m.group(2)
            elif re.match(r'^artist$', m.group(1), re.I):
                return Artist.name == m.group(2)
            elif re.match(r'^(title|track)$', m.group(1), re.I):
                return Track.name == m.group(2)
            elif re.match(r'^path$', m.group(1), re.I):
                return or_(Release.dirpath == m.group(2), File.path == m.group(2))
        
        # TODO add more regex filters
        # TODO add +tag filters
        # TODO add singleton:(1|true) like boolean value filters
        return or_(Artist.name.like('%' + field + '%'), Release.name.like('%' + field + '%'), Track.title.like('%' + field + '%') )

    # }}} end get_clause(self, field)

    def add(self, item):
        """Add a Item (track, release, artist, etc) to the database"""
        if item != None and isinstance(item, Base):
            # save without passing item_id, item should insert into the database if
            # it does not have an item_id and save is not passed one
            self.session.add(item)

    def artist(self, artist_id):
        return self.session.query(Artist).filter(Artist.id == artist_id).first()


    def artists(self, fields=None):
        """Return a list of Artist objects from the database base on fields
        If no fields then return all artist in database
        """
        filters = [ ]
        if isinstance(fields, list) and len(fields) > 0:
            for field in fields:
                filters.append(self.get_filter(field))

            return self.session.query(Artist).filter(filters).all()
        elif fields != None:
            return self.session.query(Artist).join(Track).join(File).join(Release).filter(self.get_filter(fields)).all()

        return self.session.query(Artist).all()

    def release(self, release_id):
        return self.session.query(Release).filter(Release.id == release_id).first()

    def releases(self, fields=None):
        """Return a list of release objects from the database base on fields
        If no fields then return all releases in database
        """
        # TODO: add support for various artist release search
        filters = [ ]
        if isinstance(fields, list) and len(fields) > 0:
            for field in fields:
                filters.append(self.get_filter(field))

            return self.session.query(Release).join(Artist).join(Track).join(File).filter(filters).all()

        elif fields != None:
            return self.session.query(Release).join(Artist).join(Track).join(File).filter(self.get_filter(fields)).all()
        
        return self.session.query(Release).all()

    def track(self, track_id):
        return self.session.query(Track).filter(Track.id == track_id).first()

    def tracks(self, fields=None):
        """Return a list of track objects from the database base on fields
        If no fields then return all tracks in database
        """
        # TODO: add support for featured artist track search
        filters = [ ]
        if isinstance(fields, list) and len(fields) > 0:
            for field in fields:
                filters.append(self.get_filter(field))

            return self.session.query(Track).join(Artist).join(Release).join(File).filter(filters).all()

        elif fields != None:
            return self.session.query(Track).join(Artist).join(Release).join(File).filter(self.get_filter(fields)).all()

        return self.session.query(Track).all()

# }}} end Library(BaseLibrary)

