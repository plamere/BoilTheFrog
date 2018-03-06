import sys
import rocksdb
import time
import collections
import json
import random
import spotipy
import spotipy_util as util
from spotipy.oauth2 import SpotifyClientCredentials

js_nodes = 'g2/nodes.js'
js_edges = 'g2/edges.js'
js_nodes = 'g4/nodes.js'
js_edges = 'g4/edges.js'
db_path = 'rocks2.db'
read_only = False
total_runs = 1


server_side_credentials = False

if server_side_credentials:
    client_credentials_manager = SpotifyClientCredentials()
    spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
else:
    scope = ''
    username = 'plamere'
    token = util.prompt_for_user_token(username, scope, use_web_browser=False)
    if token:
        spotify = spotipy.Spotify(auth=token)
    else:
        print "can't get token"


def to_tiny_artist(artist):
    image = None
    if len(artist['images']) > 0:
        image = artist['images'][0]['url']
    ta = {
        "id": artist['id'],
        "name": artist['name'],
        "followers": artist['followers']['total'],
        "popularity": artist['popularity'],
        "image": image,
        "genres": artist['genres']
    }
    return ta

def to_tiny_track(track):
    if len(track['album']['images']) > 0:
        image = track['album']['images'][0]['url']
    else:
        image = None

    tt = {
        "id": track['id'],
        "name": track['name'],
        "audio": track['preview_url'],
        "image": image
    }
    return tt


def build():
    db = rocksdb.DB(db_path, rocksdb.Options(create_if_missing=True))
    edge_map = load_edges(js_edges)

    f = open(js_nodes)
    for i, line in enumerate(f):
        try:
            artist = json.loads(line.strip())
            tiny_artist = to_tiny_artist(artist)
            if tiny_artist['id'] in edge_map:
                tiny_artist['edges'] = edge_map[tiny_artist['id']]
            else:
                tiny_artist['edges'] = []
            db.put(tiny_artist['id'], json.dumps(tiny_artist))
            print i, tiny_artist['name']
        except:
            print "trouble with artist", line
            continue
    f.close()

def dump_nodes():
    f = open(js_nodes)
    for i, line in enumerate(f):
        try:
            artist = json.loads(line.strip())
            tiny_artist = to_tiny_artist(artist)
            print "%7d %s" % (tiny_artist['followers'], tiny_artist['name'])
        except:
            print "trouble with", line
            continue
    f.close()

def load_edges(path):
    edge_map = {}
    f = open(path)
    for line in f:
        try:
            edge_dict = json.loads(line.strip())
            for uri, edges in edge_dict.items():
                tid = uri_to_tid(uri)
                tedges = []
                for edge in edges:
                    tedges.append(uri_to_tid(edge))
                edge_map[tid] = tedges
        except:
            print "trouble with edge", line
            continue
    f.close()
    return edge_map
    

def add_track_info():
    db = rocksdb.DB(db_path, rocksdb.Options(create_if_missing=False))
    it = db.itervalues()
    it.seek_to_first()
    missing = []
    for i, tartist_js in enumerate(it):
        tartist = json.loads(tartist_js)
        if 'tracks' not in tartist or len(tartist['tracks']) == 0 or has_no_audio(tartist['tracks']):
            missing.append(tartist)

    print "artists missing tracks", len(missing)
    missing.sort(key=lambda a:a['followers'], reverse=True)
    for i, artist in enumerate(missing):
        add_tracks(artist)
        if not 'incoming_edges' in artist:
            artist['incoming_edges'] = []
        if not 'edges' in artist:
            artist['edges'] = []
        db.put(artist['id'], json.dumps(artist))
        print i, len(missing), len(artist['tracks']), artist['followers'], artist['id'], artist['name']
    print "artists missing tracks", len(missing)

def port_tracks(old_db, new_db):
    odb = rocksdb.DB(old_db, rocksdb.Options(create_if_missing=False))
    ndb = rocksdb.DB(new_db, rocksdb.Options(create_if_missing=False))
    it = ndb.itervalues()
    it.seek_to_first()
    for i, tartist_js in enumerate(it):
        tartist = json.loads(tartist_js)
        oartist = get_artist(odb, tartist['id'])
        if oartist and 'tracks' in oartist and len(oartist['tracks']) > 0:
            tartist['tracks'] = oartist['tracks']
            ndb.put(tartist['id'], json.dumps(tartist))
            print i, len(tartist['tracks'])

def has_no_audio(tracks): 
    for track in tracks:
        if 'audio' in track and track['audio'] != None:
            return False
    return True

def has_no_audio(tracks): 
    for track in tracks:
        if 'audio' in track and track['audio'] != None:
            return False
    return True



def add_incoming_edges():

    db = rocksdb.DB(db_path, rocksdb.Options(create_if_missing=False))
    it = db.itervalues()
    it.seek_to_first()

    incoming_edges = collections.defaultdict(list)
    all_ids = set()

    for i, tartist_js in enumerate(it):
        tartist = json.loads(tartist_js)
        source = tartist['id']
        all_ids.add(source)
        if i % 1000 == 0:
            print i, tartist['name']
        if 'edges' in tartist:
            for edge in tartist['edges']:
                incoming_edges[edge].append(source)

    for i, aid in enumerate(all_ids):
        artist = get_artist(db, aid)
        artist['incoming_edges'] = incoming_edges[artist['id']]
        db.put(artist['id'], json.dumps(artist))
        if i % 1000 == 0:
            print i, artist['name'], len(artist['incoming_edges'])

def add_tracks(artist):
    results = spotify.artist_top_tracks(artist['id'], country='SE')
    #print json.dumps(results, indent=4)
    tracks = []
    for track in results['tracks']:
        ttrack = to_tiny_track(track)
        tracks.append(ttrack)
    artist['tracks'] = tracks

def id_to_uri(tid):
    if not tid.startswith('spotify:artist:'):
        return 'spotify:artist:' + tid
    return tid

def uri_to_tid(uri):
    return uri.split(':')[-1]

def get_artist(db, uri_or_tid):
    tid = uri_to_tid(uri_or_tid)
    tjs = db.get(tid)
    if tjs:
        tartist = json.loads(tjs)
    else:
        tartist = None
    return tartist

def test_getter(total_runs=1):
    db = rocksdb.DB(db_path, rocksdb.Options(), read_only=True)
    errs = 0
    total_time = 0
    count = 0
    f = open(js_nodes)
    tartists = []
    for i, line in enumerate(f):
        artist = json.loads(line.strip())
        tiny_artist = to_tiny_artist(artist)
        tartists.append(tiny_artist)

    while total_runs:
        random.shuffle(tartists)
        for i, tiny_artist in enumerate(tartists):
            start = time.time()
            tartist = get_artist(db, tiny_artist['id'])
            delta = time.time() - start
            total_time += delta

            count += 1
            if tiny_artist['name'] == tartist['name']:
                print i, total_runs, errs, tiny_artist['name'], '==', tartist['name']
            else:
                print 'MISMATCH', i, total_runs, errs, tiny_artist['name'], '==', tartist['name']
                errs += 1
        total_runs -= 1
    f.close()

    print "errors", errs
    print "total_time", total_time, "ms per read",  total_time * 1000 / count

if __name__ == '__main__':
    args = sys.argv[1:]
    uris = []
    while args:
        arg = args.pop(0)

        if arg == '--build':
            build()
        elif arg == '--artist' and args and not args[0].startswith('--'):
            uris.append(args.pop(0))
        elif arg == '--dump':
            db = rocksdb.DB(db_path, rocksdb.Options(), read_only=True)
            for uri in uris:
                artist = get_artist(db, uri)
                print json.dumps(artist, indent=4)
                print
        elif arg == '--dump-nodes':
            dump_nodes()
        elif arg == '--add-tracks':
            add_track_info()
        elif arg == '--add-incoming-edges':
            add_incoming_edges()

        elif arg == '--port-tracks':
            old_path = args.pop(0)
            port_tracks(old_path, db_path)
        elif arg == '--db' and args and not args[0].startswith('--'):
            db_path = args.pop(0)
        elif arg == '--test':
            test_getter(total_runs)
        elif arg == '--ptest':
            artist = { 'id': '6jJ0s89eD6GaHleKKya26X' }
            add_tracks(artist)
            print json.dumps(artist, indent=4)
        elif arg == '--runs' and args:
            total_runs = int(args.pop(0))
