import networkx as nx
import db
import json
import pydot
import codecs
from networkx.algorithms import approximation

trace=True


def load_graph(dbpath):
    G = nx.Graph()
    max_edges_per_node = 100
    db.load_db(dbpath)

    edges = db.get_all_edges()

    for node, targets in edges.items():
        for i, target in enumerate(targets[:max_edges_per_node]):
            add_edge(G, node, target)

    if trace:
        print "nodes", G.number_of_nodes()
        print "edges", G.number_of_edges()
        print "connnected components", len(list(nx.connected_components(G)))

    return G

def add_node(G, node, **kwargs):
    if node not in G:
        G.add_node(node, name=db.get_artist(node)['name'])
    for key, value in kwargs.iteritems():
        G.node[node][key] = value

def add_edge(G, source, target):
    add_node(G, source)
    add_node(G, target)
    source_pop = db.get_artist(source)['popularity']
    target_pop = db.get_artist(target)['popularity']
    delta = abs(source_pop - target_pop)
    weight = delta = .1 + delta / 200.0
    G.add_edges_from([(source, target, {"weight": weight})])

def mst(G):
    return nx.minimum_spanning_tree(G)

def path(G, source, target):
    return nx.bidirectional_dijkstra(G, source, target)



def build_sub_graph2(G, uris):
    """ given a set of edges build a subgraph
        that connects these edges
    """

    original_uris = set(uris)
    SG = nx.Graph()
    missing = 0
    for uri in uris:
        if not uri in G.nodes:
            missing += 1
            print "missing", uri
    print "missing", missing, "artists"

    artists = db.get_artists(uris)
    artists.sort(key=lambda a:a['popularity'], reverse=True)
    remaining_uris = [ artist['uri'] for artist in artists]
    source_uri = remaining_uris.pop(0)

    all_known_paths = shortest_paths(G, source_uri, remaining_uris)
    while all_known_paths:
        length, source, target, path = all_known_paths.pop(0)

        print "BSG", len(all_known_paths), len(remaining_uris), len(SG.nodes), length, source, target

        if target not in SG.nodes:
            remaining_uris.remove(target)
            last = None
            for node in path:
                if node not in SG.nodes:
                    add_node(SG, node, bridge_node=node not in original_uris)
                if last:
                    add_edge(SG, last, node)
                last = node
            all_known_paths.extend(shortest_paths(G, target, remaining_uris))
            all_known_paths.sort()
    return SG


def build_sub_graph(G, uris):
    return approximation.steinertree.steiner_tree(G, uris)

def build_sub_graph(G, uris):
    SG = G.subgraph(uris)
    return SG

def build_sub_graph3(G, uris):
    SG = G.subgraph(uris).copy()
    clusters = list(nx.connected_components(SG))
    main_cluster = set(clusters[0])
    for cluster in clusters[1:]:
        #source = cluster.pop() # todo perhaps use most popular?
        source = get_top_artist_from_cluster(cluster)
        paths = shortest_paths(G, source, main_cluster, 3)
        length, source, target, path = paths[0]
        last = None
        for node in path:
            main_cluster.add(node)
            add_node(SG, node, bridge_node = node not in uris)
            if last:
                add_edge(SG, last, node)
            last = node

    #SG = nx.minimum_spanning_tree(SG)
    return SG

def build_sub_graph4(G, uris):
    return nx.minimum_spanning_tree(build_sub_graph3(G, uris))

def get_top_artist_from_cluster(cluster):
    lcluster = list(cluster)
    lcluster.sort(key=lambda uri:db.get_artist(uri)['popularity'], reverse=True)
    return lcluster[0]

def shortest_paths(G, source, targets, acceptable_length=None):
    paths = []
    for target in targets:
        length, path = nx.bidirectional_dijkstra(G, source, target)
        paths.append((length, source, path[-1], path))
        if acceptable_length and length <= acceptable_length:
            break
    paths.sort()
    return paths

def save_graph(G, path):
    for edge in G.edges():
        print edge

def an(uri):
    return db.get_artist_name(uri).encode("utf-8")
    #return db.get_artist_name(uri)

def au(uri):
    return uri.split(':')[2]

def print_graph(SG):
    for edge in SG.edges():
        print "  %s -> %s" % (an(edge[0]), an(edge[1]))

def dump_graph_as_js(path, SG):
    obj = nx.node_link_data(SG)
    f = open(path, "w")
    print >>f, "var myGraph=",json.dumps(obj, indent=4), ";"
    f.close()


def dump_graph(path, SG):
    js_path = path.replace(".dot", ".js")
    dump_graph_as_js(js_path, SG)

    f = open(path, "w")
    #f = codecs.open(path, "w", encoding= "utf-8")
    print >> f, "graph {"
    print >> f, "    graph [overlap=false];"
    for edge in SG.edges():
        print >> f, '  "%s" -- "%s";' % (au(edge[0]), au(edge[1]))

    print >>f
    for node in SG.nodes():
        nnode = SG.node[node]
        if 'bridge_node' in nnode and nnode['bridge_node']:
            shape = 'plain'
        else:
            shape = 'ellipse'
        try:
            print >> f, '  "%s" [shape=%s, label="%s"];' % (au(node), shape, an(node))
        except:
            pass
            
    print >> f, "}"
    f.close()

if __name__ == '__main__':
    G = load_graph()


