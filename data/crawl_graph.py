import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import os
import urllib2
import time
import codecs

from pyechonest import artist, config, util
config.TRACE_API_CALLS=False


queue = []
sim_done = set()
S = '<sep>'
RS = ' <sep> '
min_hotttnesss = .4
idspace = 'spotify-WW'
idspace = 'spotifyv2-ZZ'


def get_hottest():
    maxh = 0
    for i in xrange(len(queue)):
        hot = queue[i][0]
        if hot > maxh:
            best = i
            maxh = hot
    return queue.pop(best)

def enc(s):
    return s
    # return s.encode('UTF-8')

def short_fid(fid):
    return fid.split(':')[-1]

def crawl():
    while len(queue) > 0:
        hot, id, fid, name = get_hottest()
        sfid = short_fid(fid)
        if id in sim_done:
            continue
        print "%4d %4d %.3f %s" % (len(sim_done), len(queue), hot, name)

        print >> outfile, 'artist', S, id, S, name, S, sfid, S, hot
        try:
            sims = artist.similar(ids=[id], results=12, buckets=['hotttnesss', 'familiarity', 'id:' + idspace], limit=True, min_hotttnesss=min_hotttnesss)
            for s in sims:
                proc_artist(s)
            for s in sims:
                simfid = s.get_foreign_id(idspace=idspace)
                ssimfid = short_fid(simfid)
                try:
                    print >>outfile, 'sim', S, id, S, name, S, s.id, S, s.name, S, s.hotttnesss, S, ssimfid
                    if s.id not in sim_done:
                        queue.append( (s.hotttnesss, s.id, simfid, s.name) )
                except UnicodeDecodeError:
                    print "skipping artist because of unicode error", s.id
            sim_done.add(id)
        except urllib2.URLError:
            time.sleep(10)
        except util.EchoNestAPIError:
            time.sleep(5)


def proc_artist(a):
    if a.id not in sim_done:
        fid = a.get_foreign_id(idspace=idspace)

def queue_by_name(name):
    results = artist.search(name, buckets=['hotttnesss', 'familiarity', 'id:' + idspace], results=1, limit=True)
    for r in results:
        fid = r.get_foreign_id(idspace=idspace)
        queue.append( (r.hotttnesss, r.id, fid, r.name) )


def load(path):
    tqueue = []
    for line in open(path):
        line = line.strip()
        print >> outfile, line
        fields = line.split(RS)
        if fields[0] == 'artist':
            sim_done.add(fields[1])
            name = fields[2]
            hot = float(fields[4])
            print "%4d %4d %.3f %s" % (len(sim_done), len(queue), hot, name)
        elif fields[0] == 'sim':
            id = fields[3]
            name = fields[4]
            hot = float(fields[5])
            fid = fields[6]
            if not id in sim_done:
                tqueue.append( (hot, id, fid, name) )

    for fields in tqueue:
        if not fields[1] in sim_done:
            queue.append(fields)


if __name__ == '__main__':
    outpath = sys.argv[-1]
    if not os.path.exists(outpath):
        outfile = open(outpath, 'w')
        if len(sys.argv) == 3:
            load(sys.argv[-2])
        else:
            queue_by_name('weezer')
            queue_by_name('lady gaga')
            queue_by_name('miles davis')
            queue_by_name('Led Zeppelin')
            queue_by_name('Explosions in the sky')
            queue_by_name('kanye west')
        crawl()
    else:
        print "won't override", outpath

