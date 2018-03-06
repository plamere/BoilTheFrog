import cmd
import artist_graph
import simplejson as json
import time

class ArtistGraphShell(cmd.Cmd):
    prompt = "ag% "
    ag = artist_graph.ArtistGraph()
    raw = False
    skips = set()

    def do_test(self, line):
        print self.my_redis
        print 'hello world'

    def do_EOF(self, line):
        return True

    def do_toggle_raw(self, line):
        self.raw = not self.raw
        return True

    def do_skip(self, line):
        if len(line) == 0:
            for s in self.skips:
                print self.an(s),
            print
        elif line == 'clear':
            self.skips = set()
        else:
            artists = line.split(",")
            for artist in artists:
                aid = self.ag.search(line)
                if aid:
                    self.skips.add(aid)
            
    def an(self, aid):
        return self.ag.get_artist(aid)['name']

    def do_path(self, line):
        artists = line.split(",")
        if len(artists) == 2:
            results = self.ag.path(artists[0].strip(), artists[1].strip(), self.skips)
            if self.raw:
                print json.dumps(results, indent=4)
            if results['status'] == 'ok':
                dump_path(results['path'])
                print "time:", results['pdelta'], results['fdelta']
            else:
                print results['status']
                print results['reason']
        else:
            print "usage: path artist1, artist2"

    def do_edge_check(self, line):
        aid = self.ag.search(line)
        if aid:
            self.ag.edge_check(aid)

    def do_sim_check(self, line):
        aid = self.ag.search(line)
        if aid:
            self.ag.sim_check(aid)


def dump_path(path):
    for i, artist in enumerate(path):
        print  "%2d %2d %s %s" % (i, artist['popularity'], artist['id'], artist['name'])

if __name__ == '__main__':
    ArtistGraphShell().cmdloop()
