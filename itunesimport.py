from pyItunes import *
from configobj import ConfigObj
import musicbrainz2.webservice as ws
import musicbrainz2.model as m
import musicbrainz2.utils as u
import string
import time
import os
import sqlite3
from headphones import FULL_PATH

database = os.path.join(FULL_PATH, 'headphones.db')


def itunesImport(pathtoxml):
	pl = XMLLibraryParser(pathtoxml)
	l = Library(pl.dictionary)
	lst = []
	for song in l.songs:
		lst.append(song.artist)
	rawlist = {}.fromkeys(lst).keys()
	artistlist = [f for f in rawlist if f != None]
	for name in artistlist:
		artistResults = ws.Query().getArtists(ws.ArtistFilter(string.replace(name, '&#38;', '%38'), limit=1))		
		for result in artistResults:
			artistid = u.extractUuid(result.artist.id)
			inc = ws.ArtistIncludes(releases=(m.Release.TYPE_OFFICIAL, m.Release.TYPE_ALBUM), ratings=False, releaseGroups=False)
			artist = ws.Query().getArtistById(artistid, inc)
			conn=sqlite3.connect(database)
			c=conn.cursor()
			c.execute('CREATE TABLE IF NOT EXISTS artists (ArtistID TEXT UNIQUE, ArtistName TEXT, ArtistSortName TEXT, DateAdded TEXT, Status TEXT)')
			c.execute('CREATE TABLE IF NOT EXISTS albums (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, ReleaseDate TEXT, DateAdded TEXT, AlbumID TEXT UNIQUE, Status TEXT)')
			c.execute('CREATE TABLE IF NOT EXISTS tracks (ArtistID TEXT, ArtistName TEXT, AlbumTitle TEXT, AlbumASIN TEXT, AlbumID TEXT, TrackTitle TEXT, TrackDuration TEXT, TrackID TEXT)')
			c.execute('SELECT ArtistID from artists')
			artistlist = c.fetchall()
			if any(artistid in x for x in artistlist):
				pass
			else:
				c.execute('INSERT INTO artists VALUES( ?, ?, ?, CURRENT_DATE, ?)', (artistid, artist.name, artist.sortName, 'Active'))
				for release in artist.getReleases():
					releaseid = u.extractUuid(release.id)
					inc = ws.ReleaseIncludes(artist=True, releaseEvents= True, tracks= True, releaseGroup=True)
					results = ws.Query().getReleaseById(releaseid, inc)
					time.sleep(1)
					for event in results.releaseEvents:
						if event.country == 'US':
							c.execute('INSERT INTO albums VALUES( ?, ?, ?, ?, ?, CURRENT_DATE, ?, ?)', (artistid, results.artist.name, results.title, results.asin, results.getEarliestReleaseDate(), u.extractUuid(results.id), 'Skipped'))
							conn.commit()
							c.execute('SELECT ReleaseDate, DateAdded from albums WHERE AlbumID="%s"' % u.extractUuid(results.id))
							latestrelease = c.fetchall()
							if latestrelease[0][0] > latestrelease[0][1]:
								c.execute('UPDATE albums SET Status = "Wanted" WHERE AlbumID="%s"' % u.extractUuid(results.id))
							else:
								pass
							for track in results.tracks:
								c.execute('INSERT INTO tracks VALUES( ?, ?, ?, ?, ?, ?, ?, ?)', (artistid, results.artist.name, results.title, results.asin, u.extractUuid(results.id), track.title, track.duration, u.extractUuid(track.id)))
								conn.commit()
								c.close()
						else:
							pass
		