import sys
import json
import spotipy
import db
from spotipy.oauth2 import SpotifyClientCredentials

max_artists = 100000
client_credentials_manager = SpotifyClientCredentials()
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

known_artists = set()
expanded_artists = set()
queue = []



def process_queue(nodefile, edgefile):
    edge_count = 0


    while queue and len(known_artists) < max_artists:
        artist = queue.pop(0)
        uri = artist['uri']
        if uri in expanded_artists:
            continue

        expanded_artists.add(uri)
        results = spotify.artist_related_artists(uri)
        for sim_artist in results['artists']:
            print "        %s =>  %s" % (artist['name'], sim_artist['name'])

        sim_uris = []
        for sim_artist in results['artists']:
            edge_count += 1
            sim_uri = sim_artist['uri']
            if sim_uri not in known_artists:
                known_artists.add(sim_uri)
                print "%5d/%-7d %7d %s %3d %7d %s" % (len(known_artists), len(queue), edge_count, sim_uri,
                sim_artist['popularity'], sim_artist['followers']['total'], sim_artist['name'])
                queue.append(sim_artist)
                print >> nodefile,  json.dumps(sim_artist)
            sim_uris.append(sim_artist['uri'])
        #queue.sort(key=lambda a:a['popularity'], reverse=True)
        queue.sort(key=lambda a:a['followers']['total'], reverse=True)

        dict = { artist['uri']: sim_uris }
        print >> edgefile, json.dumps(dict)

            # print "   %s %s => %s %s" % (artist['uri'], artist['name'], sim_artist['uri'], sim_artist['name'])


if __name__ == '__main__':

    seeds = [ 
        'spotify:artist:3hE8S8ohRErocpkY7uJW4a', # within temptation
        'spotify:artist:0kbYTNQb4Pb1rPbbaF0pT4', # miles davis
        'spotify:artist:3WrFJ7ztbogyGnTHbHJFl2', # the beatles
        'spotify:artist:6eUKZXaKkcviH0Ku9w2n3V', # ed sheeran
        'spotify:artist:36QJpDe2go2KgaRleHCDTp', # led zeppelin
    ]

    args = sys.argv[1:]
    prefix = "./"

    while args:
        arg = args.pop(0)

        if arg == '--path':
            prefix = args.pop(0)

        elif arg == '--load':
            db.load_db(prefix)

            artists = db.get_all_artists()

            for uri, artist in artists.items():
                known_artists.add(uri)

            edges = db.get_all_edges()

            for source, targets in edges.items():
                expanded_artists.add(source)

            for source, targets in edges.items():
                expanded_artists.add(source)

                for target in targets:
                    if target not in expanded_artists:
                        artist = db.get_artist(target)
                        if artist:
                            queue.append(artist)
                        else:
                            print "trouble on restart, unknown artist", artist

            nodefile = open(prefix + '/nodes.js', 'a')
            edgefile = open(prefix + '/edges.js', 'a')
            #queue.sort(key=lambda a:a['popularity'], reverse=True)
            queue.sort(key=lambda a:a['followers']['total'], reverse=True)
            process_queue(nodefile, edgefile)

        elif arg == '--fresh':
            nodefile = open(prefix + '/nodes.js', 'w')
            edgefile = open(prefix + '/edges.js', 'w')
            for seed in seeds:
                artist = spotify.artist(seed)
                known_artists.add(seed)
                queue.append(artist)
                print >> nodefile,  json.dumps(artist)

            process_queue(nodefile, edgefile)

            queue.sort(key=lambda a:a['popularity'], reverse=True)
