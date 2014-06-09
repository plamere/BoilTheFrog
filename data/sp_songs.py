import requests
import pprint
import simplejson as json
import atexit
import os
import sys

import spotipy


spotify = spotipy.Spotify()

ECHO_NEST_API_KEY='EHY4JJEGIOFA1RCJP'

playlist = 'http://developer.echonest.com/api/v4/playlist/static?api_key=%s&artist_id=%s&results=10&type=artist&bucket=id:rdio-US&bucket=tracks&limit=true&bucket=audio_summary'

search = 'http://developer.echonest.com/api/v4/song/search?api_key=%s&artist_id=%s&results=10&sort=song_hotttnesss-desc&bucket=id:rdio-US&bucket=tracks&limit=true&bucket=audio_summary'

path = 'song-data.dat'

def fetch_songs(id):
    url = playlist % (ECHO_NEST_API_KEY, id)
    r = requests.get(url)
    results = None
    if r.status_code == 200:
        results = json.loads(r.text)
        # pprint.pprint(results)
        results = results['response']['songs']
    return results

def fetch_songs2(id):
    url = search % (ECHO_NEST_API_KEY, id)
    r = requests.get(url)
    results = None
    if r.status_code == 200:
        results = json.loads(r.text)
        # pprint.pprint(results)
        results = results['response']['songs']
    return results

def fetch_rdio_tracks(id):
    songs = fetch_songs(id)
    if songs == None or len(songs) == 0:
        songs = fetch_songs2(id)
    all = []
    for s in songs:
        rs = {}
        rs['energy'] = s['audio_summary']['energy']
        rs['title'] = s['title']
        rs['id'] = s['id']
        rdio_id = s['tracks'][0]['foreign_id']
        rdio_id = rdio_id.replace('rdio-US:track:', '')
        rs['rdio_id'] = rdio_id
        all.append(rs)
    return all


def get_best_album_art(images, min_width):
    best = images[0]
    for image in images:
        if image['width'] < min_width:
            break
        best = image
    return best['url'];

def get_simple_id(sid):
    fields = sid.split(':')
    if len(fields) == 3:
        return fields[2]
    else:
        return sid

def fetch_spotify_tracks(id):
    max_tracks_per_artist = 5
    response = spotify.artist_top_tracks(id)
    try:
        tracks = response['tracks']
    except spotify.SpotifyException:
        tracks = []
        print 'exception for', id

    if tracks == None or len(tracks) == 0:
        print 'missing tracks for', id
    all = []
    for track in tracks:
        rs = {}
        rs['energy'] = .5
        rs['title'] = track['name']
        rs['id'] = track['id']

        if 'preview_url' not in track:
            continue

        if 'album' not in track or 'images' not in track['album']:
            continue

        images = track['album']['images']
        if len(images) == 0:
            continue

        rs['audio'] = track['preview_url']
        rs['album_art'] = get_best_album_art(images, 250)

        all.append(rs)
        if len(all) >= max_tracks_per_artist:
            break

    return all

hash = {}
dirty = False

def flush_hash():
    global dirty
    if dirty:
        dirty = False
        print 'flushing hash'
        out = open(path, 'w')
        shash = json.dumps(hash)
        print >> out, shash
        out.close()

def load_hash():
    hash = {}
    if os.path.exists(path):
        file = open(path)
        shash = file.read()
        hash = json.loads(shash)
        file.close()
    return hash
    
# artist <sep> ARX6TAQ11C8A415850 <sep> Lady Gaga <sep> 1HY2Jd0NmPuamShAr6KMms <sep> 0.839888
# sim <sep> ARX6TAQ11C8A415850 <sep> Lady Gaga <sep> ARORMBJ1241B9CDB1A <sep> Ke$ha <sep> 0.749993 <sep> 6LqNN22kT3074XbTVUrhzX
def load_graph(path):
    RS = ' <sep> '
    artists = []
    seen = set()

    for i, line in enumerate(open(path)):
        fields = line.strip().split(RS)
        if i % 100000 == 0:
            print i, fields[2]
        if fields[0] == 'artist' and len(fields) > 4:
            artist = { 'id' : fields[1], 'name' : fields[2], 'sid' : fields[3], 'hot': float(fields[4]) }
        elif fields[0] == 'sim' and len(fields) > 6:
            artist = { 'id' : fields[3], 'name' : fields[4], 'sid' : fields[6], 'hot': float(fields[5]) }
        else:
            continue

        if not artist['id'] in seen:
            artists.append(artist)
            seen.add(artist['id'])

    artists.sort(reverse=True, key=lambda a: a['hot'])
    return artists

def crawl_songs(path):
    global hash, dirty

    artists = load_graph(path)

    hash = load_hash()
    atexit.register(flush_hash)

    total = len(artists)
    for i, a in enumerate(artists):
        sid = a['sid']
        sid = get_simple_id(sid)
        if not sid in hash:
            print  "%d/%d %.2f %s" % (i, total, a['hot'], a['name'])
            songs = fetch_spotify_tracks(sid)
            hash[sid] = songs
            dirty = True
            if i % 1000 == 0:
                flush_hash()

if __name__ == '__main__':
    crawl_songs(sys.argv[1])
