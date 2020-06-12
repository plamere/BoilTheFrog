import sys
import json
import spotipy
import db
from spotipy.oauth2 import SpotifyClientCredentials

max_artists = 1000000
superseeds = 50000
client_credentials_manager = SpotifyClientCredentials()
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

known_artists = set()
expanded_artists = set()
queue = []

ta = 'spotifh:artist:7dGJo4pcD2V6oG8kP0tJRR' # troublesome artist
def check_ta(where, artist):
    if artist['uri'] == ta:
        print 'TA', where 

def check_ta_uri(where, uri):
    if uri == ta:
        print 'TAU', where 

def queue_append(artist):
    check_ta('queue_append', artist)
    queue.append( (artist['followers']['total'], artist['uri'], artist['name']))

def queue_sort():
    queue.sort(reverse=True)

def process_queue(nodefile, edgefile):
    edge_count = 0

    queue_sort()
    while queue and len(known_artists) < max_artists:
        followers, uri, artist_name = queue.pop(0)
        print len(queue), followers, uri, artist_name
        if uri in expanded_artists:
            print "   done"
            check_ta_uri('already expanded', uri)
            continue

        expanded_artists.add(uri)
        results = spotify.artist_related_artists(uri)
        if not results['artists']:
            print "NO SIMS FOR", artist_name
        check_ta_uri('goit sims', uri)
        for sim_artist in results['artists']:
            print "        %s =>  %s" % (artist_name, sim_artist['name'])

        sim_uris = []
        for sim_artist in results['artists']:
            edge_count += 1
            sim_uri = sim_artist['uri']
            if sim_uri not in known_artists:
                known_artists.add(sim_uri)
                print "%5d/%-7d %7d %s %3d %7d %s" % (len(known_artists), len(queue), edge_count, sim_uri,
                    sim_artist['popularity'], sim_artist['followers']['total'], sim_artist['name'])
                queue_append(sim_artist)
                print >> nodefile,  json.dumps(sim_artist)
            sim_uris.append(sim_artist['uri'])
        queue_sort()

        check_ta_uri('appended sims', uri)
        dict = { uri: sim_uris }
        print >> edgefile, json.dumps(dict)

            # print "   %s %s => %s %s" % (artist['uri'], artist['name'], sim_artist['uri'], sim_artist['name'])

def load_external_artist_list(top, nodefile, dbpath=None):
    if dbpath:
        db.load_db(dbpath)
    for i, line in enumerate(open('top_artists.txt')):
        if i < top:
            fields = line.strip().split()
            uri = fields[0]
            count = int(fields[1])
            name = ' '.join(fields[2:])

            if uri not in known_artists:
                print "NEW", i, uri, count, name
                artist = None
                if dbpath:
                    artist = db.get_artist(uri)
                if not artist:
                    artist = spotify.artist(uri)
                else:
                    print "  cache hit for", name
                known_artists.add(uri)
                queue_append(artist)
                print >> nodefile,  json.dumps(artist)
        else:
            break

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
                check_ta_uri('load expanded', source)
                expanded_artists.add(source)

            for uri, artist in artists.items():
                if uri not in expanded_artists:
                    queue_append(artist)

            for source, targets in edges.items():
                for target in targets:
                    if target not in expanded_artists:
                        artist = db.get_artist(target)
                        if artist:
                            queue_append(artist)
                        else:
                            print "trouble on restart, unknown artist", artist

            nodefile = open(prefix + '/nodes.js', 'a')
            edgefile = open(prefix + '/edges.js', 'a')
            #load_external_artist_list(superseeds, nodefile)
            queue_sort()
            process_queue(nodefile, edgefile)

        elif arg == '--fresh':
            nodefile = open(prefix + '/nodes.js', 'w')
            edgefile = open(prefix + '/edges.js', 'w')
            for seed in seeds:
                artist = spotify.artist(seed)
                known_artists.add(seed)
                queue_append(artist)
                print >> nodefile,  json.dumps(artist)

            process_queue(nodefile, edgefile)

        elif arg == '--superseeds':
            seed_count = 100
            if args:
                seed_count = int(args.pop(0))
            nodefile = open(prefix + '/nodes.js', 'w')
            edgefile = open(prefix + '/edges.js', 'w')
            load_external_artist_list(seed_count, nodefile, "g2")
            process_queue(nodefile, edgefile)

