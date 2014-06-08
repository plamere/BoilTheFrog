# Boil The Frog

This is the source for a web app called BoilTheFrog that creates seamless
Spotify playlists between any two artists.  The app uses data from
the Echo Nest and Spotify to create the playlists.

The app is online at [Boil The Frog](http://static.echonest.com/BoilTheFrog)

<img src="http://static.echonest.com/BoilTheFrog/ss.png" width=600>


# The Server

Boil the Frog has a server component that provides a web API used by the app. The web API has two main entry points:

 * find_path - finds a path between two artists
 * similar - shows the similar artists for an artist

 The server relies on pre-crawled artist similarity data from the Echo Nest and song data (including links to album art and audio previews) from Spotify.  There are two python scripts that gather this data:
 
* crawl_graph.py - crawls the artist similarity data. It takes 12 to 24 hours to crawl the data for about 100 to 150K artists.
 
* sp_songs.py - crawls the top songs for each artist from Spotify. This takes about 12 hours to run.

The output data from these two scripts are loaded by the server and used to build a graph (via networkx) that is used to satisfy the find_path requests.

The server relies on cherrypy and networkx.


# The Web App
The web app is a relatively simple app that solicits artist names from the user, calls the find_path method on the server to get the path and displays the path to the user. The web audio api is used to manage playback.  The playlist can be saved to Spotify if the user allows it. The authentication code is based on this [example](https://github.com/possan/playlistcreator-example). 

