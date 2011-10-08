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
import hashlib
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
    sha1_checksum = Column(Text)
    sha1_presum = Column(Text) # first 2048 bytes of file

    def __init__(self, path=None, size=None, dateadded=None):
        self.path = path
        self.size = size
        self.dateadded = dateadded

    def exists(self):
        return self.path != None and os.path.exists(self.path)

    def checksum(self):
        if self.exists():
            self.sha1_checksum = hashlib.sha1(file(self.path, 'r').read()).hexdigest()
            self.sha1_presum = hashlib.sha1(file(self.path, 'r').read(2048)).hexdigest()
        return self.sha1_checksum if self.sha1_checksum is not None else None
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

# {{{ Tag(Base)
class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText)
    description = Column(UnicodeText)
    
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description
# }}} end Tag(Base)

# {{{ Associative Tables
track_attachments = Table('track_attachments', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('track_id', Integer, ForeignKey('tracks.id')),
        Column('attachment_id', Integer, ForeignKey(Attachment.id)) )

track_file_attachments = Table('track_file_attachments', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('track_file_id', Integer, ForeignKey('track_files.id')),
        Column('attachment_id', Integer, ForeignKey(Attachment.id)) )

release_attachments = Table('release_attachments', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('release_id', Integer, ForeignKey('releases.id')),
        Column('attachment_id', Integer, ForeignKey(Attachment.id)) )

artist_attachments = Table('artist_attachments', Base.metadata,
        Column('id', Integer, primary_key=True),
        Column('artist_id', Integer, ForeignKey('artists.id')),
        Column('attachment_id', Integer, ForeignKey(Attachment.id)) )

class TrackTag(Base):
    __tablename__ = 'track_tags'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'))
    tag_id = Column(Integer, ForeignKey(Tag.id))
    weight = Column(Integer)
    origin = Column(UnicodeText)

    tag = relationship(Tag)

class ReleaseTag(Base):
    __tablename__ = 'release_tags'

    id = Column(Integer, primary_key=True)
    release_id = Column(Integer, ForeignKey('releases.id'))
    tag_id = Column(Integer, ForeignKey(Tag.id))
    weight = Column(Integer)
    origin = Column(UnicodeText)

    tag = relationship(Tag)

class ArtistTag(Base):
    __tablename__ = 'artist_tags'

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey('artists.id'))
    tag_id = Column(Integer, ForeignKey(Tag.id))
    weight = Column(Integer)
    origin = Column(UnicodeText)

    tag = relationship(Tag)

# }}} end Associative Tables

# {{{ Artist(Base)
class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText)

    attachments = relationship(Attachment, secondary=artist_attachments)
    tags = relationship(ArtistTag)

    def __init__(self, name=None):
        self.name = name
# }}} end Artist(Base)

# {{{ SimilarArtist(Base)
class SimilarArtist(Base):
    __tablename__ = 'similar_artists'

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey('artists.id'))
    similar_artist_id = Column(Integer, ForeignKey('artists.id'))
    match_percent = Column(Integer)
    match_source = Column(UnicodeText)

    similar_artist = relationship(Artist, primaryjoin=similar_artist_id == Artist.id)
    artist = relationship(Artist, primaryjoin=artist_id == Artist.id, backref="similar_artists")

# }}} end SimilarArtist(Base)

# {{{ Release(Base)
class Release(Base):
    __tablename__ = 'releases'

    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText)
    type = Column(UnicodeText)
    artist_id = Column(Integer, ForeignKey(Artist.id))
    date = Column(Date)
    tracktotal = Column(Integer)
    disctotal = Column(Integer)
    compilation = Column(Boolean)

    artist = relationship(Artist, primaryjoin=artist_id == Artist.id, backref='releases')
    attachments = relationship(Attachment, secondary=release_attachments)
    tags = relationship(ReleaseTag)

    def __init__(self, name=None, type=None, artist=None, date=None, tracktotal=None, disctotal=None, compilation=None):
        self.name = name
        self.type = type
        self.artist = artist
        self.date = date
        self.tracktotal = tracktotal
        self.disctotal = disctotal
        self.compilation = compilation
# }}} end Release(Base)

# {{{ Track(Base)
class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey(Artist.id))
    release_id = Column(Integer, ForeignKey(Release.id))
    title = Column(UnicodeText)
    track = Column(Integer)
    disc = Column(Integer)
    genre = Column(UnicodeText)
    date = Column(Date)
    composer = Column(UnicodeText)
    length = Column(Integer)
    bpm = Column(Integer)

    artist = relationship(Artist, primaryjoin=artist_id == Artist.id, backref='tracks')
    release = relationship(Release, primaryjoin=release_id == Release.id, backref='tracks')
    attachments = relationship(Attachment, secondary=track_attachments)
    tags = relationship(TrackTag)

    # {{{ __init__(self, ...)
    def __init__(self, artist=None, release=None, title=None, track=None, disc=None, genre=None, date=None, composer=None, length=None, bpm=None):
        self.artist = artist
        self.release = release
        self.title = title
        self.track = track
        self.disc = disc
        self.genre = genre
        self.date = date
        self.composer = composer
        self.length = length
    # }}} end __init__(self, ...)

    # {{{ write(self)
    def write(self):
        """Write the track's metadata to the associated file.
        """
        for file in self.files:
            f = MediaFile(syspath(file.path))
            # TODO save values to mediafile
            f.title = self.title
            f.artist = self.artist.name
            f.album = self.release.name
            f.genre = self.genre
            f.composer = self.composer
            # f.grouping = 

            # parse time format
            # TODO: add these to beets.util
            #time_format = "%Y-%m-%d %H:%M:%S"
            #date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(self.date, time_format)))
            #f.year = date.year
            #f.month = date.month
            #f.day = date.day
            #f.date = self.date
            f.track = self.track
            f.tracktotal = self.release.tracktotal
            f.disc = self.disc
            f.disctotal = self.release.disctotal
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
            f.save()
    # }}} end write(self)
# }}} end Track(Item)

# {{{ TrackFile(Base)
class TrackFile(Base):
    __tablename__ = 'track_files'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey(Track.id))
    file_id = Column(Integer, ForeignKey(File.id))
    cover_id = Column(Integer, ForeignKey(Attachment.id))
    bitrate = Column(Integer)
    format = Column(UnicodeText)

    track = relationship(Track, primaryjoin=track_id == Track.id, backref='files')
    attachments = relationship(Attachment, secondary=track_file_attachments)
    file = relationship(File, primaryjoin=file_id == File.id)
    cover = relationship(Attachment, primaryjoin=cover_id == Attachment.id)

# }}} end TrackFile(Base)

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
    # {{{ __init__(self, dburi, path, directory, path_format)
    def __init__(self, dburi='sqlite:///musicdir.db',
                       directory='~/Music',
                       path_formats=None):
        self.directory = bytestring_path(directory)
        if path_formats is None:
            path_formats = {'default': '$artist/$album/$track $title'}
        elif isinstance(path_formats, basestring):
            path_formats = {'default': path_formats}
        self.path_formats = path_formats

        # setup database connections
        self.db = create_engine(dburi)
        self.db.echo = False
        Session.configure(bind=self.db)
        self.session = Session()

        # make sure that the database tables are created
        metadata.create_all(self.db)

    # }}} end __init__(self, path, directory, path_format, art_filename)

    # {{{ get_filter(self, obj=None, query=None, fields=None)
    def get_filter(self, obj=None, query=None, fields=None, limit=None):
        """Transform a field into a filter using python regex
        """
        if fields is None or query is None or obj is None:
            return query

        if not isinstance(fields, list):
            fields = [ fields ]

        if len(fields) < 1:
            return query
        
        # for or'ing and and'ing together later
        filters = { 'releases' : [ ], 'artists' : [ ], 'tracks' : [ ], 'paths' : [ ],  'tags' : [ ], 'other' : [ ], 'year' : [ ], 'day' : [ ], 'month' : [ ] }

        for field in fields:
            # like matches
            m = re.match(r'^(.*?):(.*?)$', field)
            if m != None:
                if re.match(r'^(album|release)$', m.group(1), re.I):
                    filters['releases'].append( Release.name.like('%' + m.group(2) + '%') )
                    continue
                elif re.match(r'^(artist|author)$', m.group(1), re.I):
                    filters['artists'].append( Artist.name.like('%' + m.group(2) + '%') )
                    continue
                elif re.match(r'^(title|track)$', m.group(1), re.I):
                    filters['tracks'].append( Track.title.like('%' + m.group(2) + '%') )
                    continue
                elif m.group(1).lower() == 'path':
                    filters['paths'].append( File.path.like('%' + m.group(2) + '%') )
                    continue
                elif m.group(1).lower() == 'year':
                    filters['year'].append(func.year(Track.date).like('%' + m.group(2) + '%'))
                    continue
                elif m.group(1).lower() == 'day':
                    filters['day'].append(func.day(Track.date).like('%' + m.group(2) + '%'))
                    continue
                elif m.group(1).lower() == 'month':
                    filters['month'].append(func.month(Track.date).like('%' + m.group(2) + '%'))
                    continue

            # exact matches
            m = re.match(r'^(.*?)=(.*?)$', field)
            if m != None:
                if re.match(r'^(album|release)$', m.group(1), re.I):
                    filters['releases'].append( Release.name == m.group(2) )
                    continue
                elif re.match(r'^(artist|author)$', m.group(1), re.I):
                    filters['artists'].append( Artist.name == m.group(2) )
                    continue
                elif re.match(r'^(title|track)$', m.group(1), re.I):
                    filters['tracks'].append( Track.title == m.group(2) )
                    continue
                elif re.match(r'^path$', m.group(1), re.I):
                    filters['paths'].append( File.path == m.group(2) )
                    continue
                elif m.group(1).lower() == 'year':
                    filters['year'].append(func.year(Track.date) == m.group(2))
                    continue
                elif m.group(1).lower() == 'day':
                    filters['day'].append(func.day(Track.date) == m.group(2))
                    continue
                elif m.group(1).lower() == 'month':
                    filters['month'].append(func.month(Track.date) == m.group(2))
                    continue

            # tag matches
            m = re.match(r'^\+(.*?)$', field)
            if m != None:
                filters['tags'].append( Tag.name == m.group(1) )
                continue

            # TODO add more regex filters
            # TODO OR tags together, this means we need to be passed a list instead
            # TODO add singleton:(1|true) like boolean value filters
            filters['other'].append( 
                    or_(Artist.name.like('%' + field + '%') \
                            , or_(Release.name.like('%' + field + '%') \
                            , Track.title.like('%' + field + '%') ) ) )
            continue
        
        # finalize filters
        final = [ ]
        if len(filters['releases']) == 1:
            query = query.filter(filters['releases'][0] )
        elif len(filters['releases']) > 1:
            query = query.filter(or_(*filters['releases']) )

        if len(filters['artists']) == 1:
            query = query.filter(filters['artists'][0] )
        elif len(filters['artists']) > 1:
            query = query.filter(or_(*filters['artists']) )

        if len(filters['tracks']) == 1:
            query = query.filter(filters['tracks'][0] )
        elif len(filters['tracks']) > 1:
            query = query.filter(or_(*filters['tracks']) )

        if len(filters['paths']) == 1:
            query = query.filter(filters['paths'][0] )
        elif len(filters['paths']) > 1:
            query = query.filter(or_(*filters['paths']) )

        if len(filters['tags']) == 1:
            query = query.filter(filters['tags'][0] )
        elif len(filters['tags']) > 1:
            query = query.filter(or_(*filters['tags']) )

        if len(filters['day']) == 1:
            query = query.filter(filters['day'][0] )
        elif len(filters['day']) > 1:
            query = query.filter(or_(*filters['day']) )

        if len(filters['month']) == 1:
            query = query.filter(filters['month'][0] )
        elif len(filters['month']) > 1:
            query = query.filter(or_(*filters['month']) )

        if len(filters['year']) == 1:
            query = query.filter(filters['year'][0] )
        elif len(filters['year']) > 1:
            query = query.filter(or_(*filters['year']) )


        if len(filters['other']) == 1:
            query = query.filter(filters['other'][0] )
        elif len(filters['other']) > 1:
            query = query.filter(and_(*filters['other']) )
        
        # add having clause if needed
        if len(filters['tags']) > 1:
            query = query.having(func.count(obj.id) >= len(filters['tags']) )

        return query
    # }}} end get_filter(self, obj=None, query=None, fields=None)

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
        if filter is not None:
            query = self.session.query(Artist).\
                    outerjoin(Track, Track.artist_id == Artist.id).\
                    outerjoin(Release, Release.id == Track.release_id).\
                    outerjoin(TrackFile, TrackFile.track_id == Track.id).\
                    outerjoin(File, File.id == TrackFile.file_id).\
                    outerjoin(ArtistTag, ArtistTag.artist_id == Artist.id).\
                    outerjoin(Tag, ArtistTag.tag_id == Tag.id)

            query = self.get_filter(obj=Artist, query=query, fields=fields)
            return query.group_by(Artist.id).all()
        else:
            return self.session.query(Artist).group_by(Artist.id).all()

    def release(self, release_id):
        return self.session.query(Release).filter(Release.id == release_id).first()

    def releases(self, fields=None):
        """Return a list of release objects from the database base on fields
        If no fields then return all releases in database
        """
        # TODO: add support for various artist release search
        if filter is not None:
            query = self.session.query(Release).\
                    outerjoin(Artist, Artist.id == Release.artist_id).\
                    outerjoin(Track, Track.release_id == Release.id).\
                    outerjoin(TrackFile, TrackFile.track_id == Track.id).\
                    outerjoin(File, File.id == TrackFile.file_id).\
                    outerjoin(ReleaseTag, ReleaseTag.release_id == Release.id).\
                    outerjoin(Tag, ReleaseTag.tag_id == Tag.id)
            query = self.get_filter(obj=Release, query=query, fields=fields)
            return query.group_by(Release.id).all()
        else:
            return self.session.query(Release).group_by(Release.id).all()

    def track(self, track_id):
        return self.session.query(Track).filter(Track.id == track_id).first()

    def tracks(self, fields=None):
        """Return a list of track objects from the database base on fields
        If no fields then return all tracks in database
        """
        # TODO: add support for featured artist track search
        if filter is not None:
            query = self.session.query(Track).\
                    outerjoin(Artist, Artist.id == Track.artist_id).\
                    outerjoin(Release, Release.id == Track.release_id).\
                    outerjoin(TrackFile, TrackFile.track_id == Track.id).\
                    outerjoin(File, File.id == TrackFile.file_id).\
                    outerjoin(TrackTag, TrackTag.track_id == Track.id).\
                    outerjoin(Tag, TrackTag.tag_id == Tag.id)

            query = self.get_filter(obj=Track, query=query, fields=fields)
            return query.group_by(Track.id).all()
        else:
            return self.session.query(Track).group_by(Track.id).all()

# }}} end Library(BaseLibrary)

