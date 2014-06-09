import requests
import pprint
import simplejson as json
import atexit
import os
import sys

path = 'song-data.dat'
opath = 'trimmed-song-data.dat'


hash = {}

def flush_hash(hash):
    print 'flushing hash'
    out = open(opath, 'w')
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
    print 'total artists', len(artists)
    return artists

def trim_songs(path):
    artists = load_graph(path)
    hash = load_hash()
    hash2 = {}

    total = len(artists)
    for i, a in enumerate(artists):
        sid = a['sid']
        if sid in hash:
            hash2[sid] = hash[sid]
    flush_hash(hash2)
    print 'total artists with songs', len(hash2)

if __name__ == '__main__':
    trim_songs(sys.argv[1])
