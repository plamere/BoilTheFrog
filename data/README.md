# Boil The Frog Crawlers

These are the tools for crawling the data for the Boil The Frog app.  There are 3 Programs:

  * crawl_graph.py - this program crawls the similarity data. It will build a connected graph of artists based upon Echo Nest similarity
  * sp_songs.py - this program crawls the Spotify Web API for top song info (album art and preview urls) for each artist
  * trim_sp_songs - trims the song data to exactly match the artist data.

## How to use:

### Crawl the data:

` % python crawl_graph.py s0.dat `

This crawls the artist similarity graph. This can take 12 to 24 hours depending on the depth of the crawl.  You can change the depth by changing min_hotttnesss. Lower values mean more artists.

If the program crashes (i.e. network goes down or you close your laptop), you can restart from where you left off like so:

` % python crawl_graph.py s0.dat s1.dat`

### crawl the songs
Get all the songs for the artist data with the command

` %python sp_songs.py s0.dat`

You can restart this if/when it crashes. It will recover from where it left off.  This creates a file called song-data.dat

song-data.dat grows to include songs for all artists, but you may want to trim the songs to exactly match a particular artist graph. use 

` %python trim_sp_songs.py s0.dat` 

to create a file called trimmed-song-data.dat with songs from song-data.dat that match the artists in s0.dat.

### Typical sequence

 ` % python crawl_graph s0.dat
 % python crawl_graph s0.dat s1.dat
 % python crawl_graph s1.dat s2.dat
 
 % python sp_songs.py s2.dat
 % python sp_songs.py s2.dat
 
 % python trim_sp_songs.py s2.dat
 
 % cp s2.dat ../server/full_spotify.dat
 % cp trimmed-song-data.dat ../server/spotify_songs.dat`
 

