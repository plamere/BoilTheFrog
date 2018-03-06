import sys
import time
import networkx as nx
import json
import rocksdb
import collections
import search


class ArtistGraph:
    def __init__(self, db_path='rocks.db'):
        self.db = rocksdb.DB(db_path, rocksdb.Options(), read_only=True)
        self.trace = True
        self.skip_artists_with_no_tracks = False
        self.max_edges_per_artist = 5
        self.searcher = search.Searcher(exact=True)

        self.artist_blacklist = set()
        self.edge_blacklist = collections.defaultdict(set)
        self.load_blacklist()

        self.load_graph()


    def load_blacklist(self):
        f = open("blacklist.csv")
        for lineno, line in enumerate(f):
            line = line.strip()
            if len(line) == 0:
                continue
            if line[0] == '#':
                continue
            fields = [f.strip() for f in line.split(',')]
            if len(fields) > 1 and fields[0] == 'artist':
                aid = to_aid(fields[1])
                self.artist_blacklist.add(aid)
            elif fields[0] == 'edge' and len(fields) > 2:
                aid1 = to_aid(fields[1])
                aid2 = to_aid(fields[2])
                self.edge_blacklist[aid1].add(aid2)
                self.edge_blacklist[aid2].add(aid1)
            else:
                print "unknown blacklist type", fields[0], "at line", lineno

    def load_graph(self):
        self.G = nx.Graph()
        max_edges_per_node = 100
        popularity = collections.defaultdict(int)

        it = self.db.itervalues()
        it.seek_to_first()
        missing = []

        if self.skip_artists_with_no_tracks:
            skips = self.get_skipset()
        else:
            skips = set()

        print "loading popularity"
        for i, tartist_js in enumerate(it):
            artist = json.loads(tartist_js)
            popularity[artist['id']] = artist['popularity']
        print len(popularity), "artists"

        print "bulding graph"
        it.seek_to_first()
        for i, tartist_js in enumerate(it):
            artist = json.loads(tartist_js)
            node = artist['id']
            if node in skips:
                continue

            if node in self.artist_blacklist:
                print 'skipped artist', node
                continue

            self.index(artist['name'],node)
            if 'edges' in artist:
                artist_edges = artist['edges'][:self.max_edges_per_artist]
                nedges = float(len(artist_edges))
                for edge, target in enumerate(artist_edges):
                    if target in skips:
                        continue

                    if target in self.artist_blacklist:
                        continue

                    if target in self.edge_blacklist[node]:
                        print 'skipped edge', node, target
                        continue

                    weight = 1.0 + edge / nedges
                    self.add_edge(node, target, weight)

            if self.trace and i % 1000 == 0:
                print "loading %d artists" % (i, )

        print "nodes", self.G.number_of_nodes()
        print "edges", self.G.number_of_edges()
        components = list(nx.connected_components(self.G))
        print "connnected components", len(components)
        clens = [len(c) for c in components]
        clens.sort(reverse=True)
        for cl in clens:
            print cl, 

    def index(self, name, aid):
        self.searcher.add(name, aid)

    def search(self, name):
        matches = self.searcher.search(name)
        if len(matches) > 0:
            return matches[0]
        else:
            return None

    def get_artist(self, aid):
        tjs = self.db.get(aid)
        if tjs:
            tartist = json.loads(tjs)
            if not 'edges' in tartist:
                tartist['edges'] = []
            if not 'incoming_edges' in tartist:
                tartist['incoming_edges'] = []
        else:
            tartist = None
        return tartist
    
    def get_skipset(self):
        skips = set()
        it = self.db.itervalues()
        it.seek_to_first()
        missing = []
        for i, tartist_js in enumerate(it):
            artist = json.loads(tartist_js)
            if 'tracks' not in artist or len(artist['tracks'])  == 0:
                skips.add(artist['id'])
        if self.trace:
            print "found %d artists with no tracks" % (len(skips),)
        return skips

    def path(self, source_name, target_name, skipset=set()):
        def get_weight(src, dest, attrs):
            if src in skipset or dest in skipset:
                # print "gw", srx, dest, attrs, 10000
                return 10000
            # print "gw", src, dest, attrs, 1
            return attrs['weight']

        results = { 
            'status': 'ok'
        }

        source_aid = self.search(source_name)
        if source_aid == None:
            results['status'] = 'error'
            results['reason'] = "Can't find " + source_name

        target_aid = self.search(target_name)
        if target_aid == None:
            results['status'] = 'error'
            results['reason'] = "Can't find " + target_name

        print "s=t", source_aid, target_aid
        if source_aid not in self.G:
            results['status'] = 'error'
            results['reason'] = "Can't find " + source_name + " in the artist graph"

        if target_aid not in self.G:
            results['status'] = 'error'
            results['reason'] = "Can't find " + target_name + " in the artist graph"

        if source_aid and target_aid and results['status'] == 'ok':
            start = time.time()
            if len(skipset) > 0:
                rpath = nx.dijkstra_path(self.G, source_aid, target_aid, get_weight)
                score = len(rpath)
            else:
                score, rpath = nx.bidirectional_dijkstra(self.G, source_aid, target_aid)
            pdelta = time.time() - start
            results['score'] = score
            populated_path = [self.get_artist(aid) for aid in rpath]
            fdelta = time.time() - start
                
            results['status'] = 'ok'
            results['raw_path'] = rpath
            results['path'] = populated_path
            results['pdelta'] = pdelta * 1000
            results['fdelta'] = fdelta * 1000
        return results

    def add_node(self, node):
        if node not in self.G:
            self.G.add_node(node)

    def add_edge(self,  source, target, weight):
        self.add_node(source)
        self.add_node(target)
        self.G.add_edges_from([(source, target, {"weight": weight})])


    def normalize_name(self, name):
        name = name.lower().strip()
        return name

    def an(self, aid):
        #return self.get_artist(aid)['name']
        artist = self.get_artist(aid)
        return "%s(%d)" % (artist['name'], artist['popularity'])

    def edge_check(self, uri):
        aid = to_aid(uri)
        artist = self.get_artist(aid)

        print "edge check", self.an(aid)

        combined = set()
        combined.union(artist['edges'])
        combined.union(artist['incoming_edges'])
            
        print "combined:"
        for aid in combined:
            print "   ", self.an(aid)
        print

        print "outgoing:"
        for aid in artist['edges']:
            if aid not in combined:
                print "   ", self.an(aid)
        print
        print "incoming:"
        for aid in artist['incoming_edges']:
            if aid not in combined:
                print "   ", self.an(aid)
        print

    def sim_check(self, uri):
        aid = to_aid(uri)
        artist = self.get_artist(aid)

        if not 'edges' in artist:
            print "leaf node, nothing to do"
            return 

        sim_counts = collections.Counter()
        osim_counts = collections.Counter()

        simset = set(artist['edges'])
        print "sim_check", self.an(aid)
        print
        print "normal sims"
        for i, edge in enumerate(artist['edges']):
            print "   %d %s %s" % (i, edge, self.an(edge))
            sim_artist = self.get_artist(edge)
            if 'edges' in sim_artist:
                for sedge in sim_artist['edges']:
                    if sedge in simset:
                        sim_counts[sedge] += 1
                    osim_counts[sedge] += 1
        print

        print "ranked sims"
        print artist['name']
        for edge, count in sim_counts.most_common():
            print "   %d %s %s"% (count, edge, self.an(edge))

        print
        print "sim neighborhooed"
        for edge, count in osim_counts.most_common():
            if count > 1:
                print "%d %s %s"% (count, edge, self.an(edge))


def to_aid(uri_or_aid):
    if uri_or_aid:
        fields = uri_or_aid.split(':')
        if len(fields) == 3:
            return fields[2]
    return uri_or_aid

if __name__ == '__main__':
    args = sys.argv[1:]
    uris = []

    ag = ArtistGraph()

    while args:
        arg = args.pop(0)
        if arg == '--path':
            pass


