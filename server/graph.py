import sys
import time
import networkx as nx
import search
import random
import os
import pprint
import simplejson as json

RS = ' <sep> '
artists ={}
aid_to_sid = {}
max_edges_per_node = 4
min_hotttnesss = .5

G = nx.Graph()

searcher = search.Searcher()
songs = {}
skips = set()

skip_artists_with_no_songs = True


def stats():
    print 'nodes', G.number_of_nodes()
    print 'edges', G.number_of_edges()
    cc = nx.connected_components(G)
    print 'components', len(cc)

    print '   ',
    for c in cc:
        print len(c),
    print
    #print 'diameter', nx.diameter(G)

def get_artist(id):
    artist = artists[id]
    return artist


def get_random_artist():
    id = random.choice(G.nodes())
    return artists[id]

def add_artist(artist):
    id = artist['id']
    if not id in artists:
        artists[id] = artist
        searcher.add(artist['name'], artist)
        G.add_node(id)
        if id in songs:
            artist['songs'] = songs[id]
            # print 'found', len(artist['songs']),  'songs for', artist['name']

def add_edge(sid, did, weight):
    G.add_edge(sid, did, weight=weight)


def npair(n1, n2):
    return n1 + ' // ' + n2


def load_skiplist(path):
    for line in open(path):
        fields = line.strip().split(RS)
        if len(fields) == 4:
            skips.add(npair(fields[0], fields[2]))
            skips.add(npair(fields[2], fields[0]))
        else:
            skips.add(fields[0])


def has_songs(id):
    return id in songs and len(songs[id]) > 0
    
def skipped(n1, n2):
    if n1 in skips:
        return True
    if n2 in skips:
        return True

    if skip_artists_with_no_songs:
        if not has_songs(n1):
            return True

        if not has_songs(n2):
            return True

    skip = npair(n1, n2) in skips
    return skip


def get_edge_weight(id1, id2):
    hot1 = artists[id1]['hot']
    hot2 = artists[id2]['hot']
    edge_weight = 1 + int(100 * (abs(hot1 - hot2)))
    # edge_weight = 1 + int(1000 * (abs(hot1 - hot2)))
    return edge_weight


def add_ids(aid, sid):
    if aid in aid_to_sid:
        if sid != aid_to_sid[aid]:
            print 'mismatched ids', aid, sid
            sys.exit(-1)
    else:
        aid_to_sid[aid] = sid
            

def load_graph(path):
    last_source = ''
    edge_count = 0
    for i, line in enumerate(open(path)):
        fields = line.strip().split(RS)
        if i % 100000 == 0:
            print i, fields[2]
        if fields[0] == 'artist':
            aid = fields[1]
            # sid = fields[3].split(':')[2]
            sid = fields[3]
            add_ids(aid, sid)
            hot = float(fields[4])
            artist = { 'id' : sid, 'name' : fields[2], 'hot': hot }
            if has_songs(sid) and hot >= min_hotttnesss:
                add_artist(artist)
        elif fields[0] == 'sim' and len(fields) > 5:
            source_aid = fields[1]
            source_sid = aid_to_sid[source_aid]
            if source_sid <> last_source:
                last_source = source_sid
                edge_count = 0

            if edge_count < max_edges_per_node:
                dest_aid = fields[3]
                #dest_sid = fields[6].split(':')[2]
                dest_sid = fields[6]
                add_ids(dest_aid, dest_sid)

                if not skipped(source_sid, dest_sid) and source_sid in artists:
                    source = artists[source_sid]
                    shot = float(fields[5])
                    dest = { 'id' : dest_sid, 'name' : fields[4], 'hot': shot }
                    if has_songs(dest['id']) and shot >= min_hotttnesss:
                        add_artist(dest)
                        edge_weight = get_edge_weight(source_sid, dest_sid)
                        add_edge(source_sid, dest['id'], edge_weight)
                        edge_count += 1

def find_artist(name):
    results = searcher.search(name)
    if len(results) > 0:
        return results[0]
    return None

def is_id(name_or_id):
    return len(name_or_id) == 18 and name_or_id.startswith('AR')

def sim_artist(name_or_id):
    if is_id(name_or_id):
        a = artists[name_or_id]
    else:
        a = find_artist(name_or_id)
    if a:
        id = a['id']
        return id, G[id].keys()
    return None, None


def sims(artist):
    return [get_artist(id) for id in G[artist['id']]]

def find_path(n1, n2, skip = []):
    start = time.time()
    path = None
    status = 'ok'

    a1 = find_artist(n1)
    a2 = find_artist(n2)

    if not a1:
        status = "Can't find " + n1
    if not a2:
        status = "Can't find " + n2

    if a1 and a2:
        if skip and len(skip) > 0:
            # graph = G.copy()
            graph = G
        else:
            graph = G

        remove_nodes(graph, skip)
        try:
            l, path = nx.bidirectional_dijkstra(graph, a1['id'], a2['id'], 'weight')

        except nx.NetworkXNoPath:
            status = 'No path found between ' + n1 + " and " + n2;
            
        restore_nodes(graph, skip)

    print 'find_path took %s seconds' % (time.time() - start,)
    return status, path

def qfind(a1, a2):
    start = time.time()
    path = None

    if a1 and a2:
        graph = G
        try:
            l, path = nx.bidirectional_dijkstra(graph, a1['id'], a2['id'], 'weight')
        except nx.NetworkXNoPath:
            pass
    return path

def remove_nodes(graph, nodes):
    if nodes:
        for n in nodes:
            for other, edge in graph[n].items():
                edge['weight'] = 10000000

def restore_nodes(graph, nodes):
    if nodes:
        for n in nodes:
            for other, edge in graph[n].items():
                edge['weight'] = get_edge_weight(n, other)


def sp(n1, n2, skip=[]):
    print '===', n1, 'to', n2, 'with', len(skip), 'skips', '==='
    iskip = []
    for n in skip:
        artist = find_artist(n)
        if artist:
            iskip.append(artist['id'])

    status, path = find_path(n1, n2, iskip)

    if path:
        for a in path:
            print artists[a]['name']
            pprint.pprint( artists[a])
            print
        
    else:
        print status

edges = set()

def edge_exists(a1, a2):
    n1 = a1+ '--' + a2
    found = n1 in edges
    if not found:
        n2 = a2 + '--' + a1
        edges.add(n1)
        edges.add(n2)
    return found
    
def gv(n1, n2, skip=[]):

    gv = open('graph.gv', 'w')
    print >>gv, "digraph {"
    iskip = []
    for n in skip:
        artist = find_artist(n)
        if artist:
            iskip.append(artist['id'])

    status, path = find_path(n1, n2, iskip)

    extra = 4
    if path:
        last = None
        for a in path:
            if last:
                neighbors = list(G[last].keys())
                neighbors.remove(a)
                #for n, attr in G[last].items()[:2]:
                for n in neighbors[0:extra]:
                    if not edge_exists(last, n):
                        print >>gv, q(last), '->', q(n) + ';'
                print >>gv, q(last), '->', q(a), '[color=red,style=bold];'
                edge_exists(last, a)
                for n in neighbors[extra: extra + 4]:
                    if not edge_exists(last, n):
                        print >>gv, q(last), '->', q(n) + ';'
            print  >>gv, q(a), '[color=red,style=bold];'
            last = a
    else:
        print status
    print >>gv, "}"
    gv.close()

def q(a):
    return '"' + artists[a]['name'] + '"'
   
def init():
    global songs

    #load_skiplist('skip_list.dat')
    songs = load_song_data('spotify_songs.dat')
    load_graph('full_spotify.dat')
    #load_graph('tiny_spotify.dat')
    stats()

def load_song_data(path):
    hash = {}
    if os.path.exists(path):
        file = open(path)
        shash = file.read()
        hash = json.loads(shash)
        file.close()
    print 'loaded', len(hash), 'songs from', path
    return hash

def test():
    sp('Miley Cyrus', 'Miles Davis')
    sp('Miley Cyrus', 'Miles Davis', [ 'Beth Orton'] )
    sp('Miley Cyrus', 'Miles Davis', [ 'Beth Orton', 'Miles Davis' ] )
    sp('Miley Cyrus', 'Miles Davis')

def test1():
    sp('Miley Cyrus', 'Britney Spears')

def test2():
    #gv('Miley Cyrus', 'Miles Davis')
    #gv('Cannibal Corpse', 'Dora the Explorer')
    gv('Kenny G', 'Nile')

if __name__ == '__main__':
    init()
    test1()
    #test2()
