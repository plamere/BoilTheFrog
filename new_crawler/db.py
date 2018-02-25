import json
import sys
import os

artists = {}
edges = {}

artist_by_name = {}

def get_artist(uri):
    if uri in artists:
        return artists[uri]
    else:
        return None

def get_artists(uris):
    return [artists[uri] for uri in uris if uri in artists]

def get_artist_name(uri):
    artist = get_artist(uri)
    if artist:
        return artist['name']
    else:
        return None

def get_artists_with_edges(uris):
    ret_artists = []
    for uri in uris:
        artist = get_artist(uri)
        if artist:
            ret_artists.append(artist)
            edges = get_edges(uri)
            if edges:
                artist['edges'] = edges
    return ret_artists

def get_edges(uri):
    if uri in edges:
        return edges[uri]
    else:
        return None

def get_all_edges():
    return edges

def get_all_artists():
    return artists


def load_db(prefix="g1"):
    if len(artists) == 0:
        f = open(prefix + "/nodes.js")
        for line in f:
            try:
                artist = json.loads(line.strip())
                artists[artist['uri']] = artist
                nname = normalize_name(artist['name'])
                artist_by_name[nname] = artist
            except:
                print "skipped bad line in db", line
        print "loaded", len(artists), "artists"

    if len(edges) == 0:
        f = open(prefix + "/edges.js")
        for line in f:
            try:
                edge = json.loads(line.strip())
                for uri, targets in edge.items():
                    edges[uri] = targets
            except:
                print "skipped bad edge in db", line
        print "loaded", len(edges), "edges"


def normalize_name(n):
    return ''.join(e.lower() for e in n if e.isalnum())

def get_artist_by_name(name):
    nname = normalize_name(name)
    print "nname", nname
    if nname in artist_by_name:
        return artist_by_name[nname]
    else:
        return None


if __name__ == '__main__':
    load_db()

    for uri in sys.argv[1:]:
        print uri
        print json.dumps(get_artist(uri), indent=4)
        print json.dumps(get_edges(uri), indent=4)
        print
    
