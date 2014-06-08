import os 
import sys
import cherrypy
import ConfigParser
import urllib2
import simplejson as json
import webtools
import time


import graph


class ArtistGraphServer(object):
    def __init__(self, config):
        self.production_mode = config.getboolean('settings', 'production')
        graph.init()


    def find_path(self, start, end, skips=None, callback=None,  _=''):
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        if callback:
            cherrypy.response.headers['Content-Type']= 'text/javascript'
        else:
            cherrypy.response.headers['Content-Type']= 'application/json'

        start_time = time.time()
        skips =  make_list(skips)
        status, path = graph.find_path(start, end, skips)
        results = {}
        results['status'] = status
        if path:
            results['path'] = [graph.get_artist(id) for id in path]
        results['time'] = time.time() - start_time
        return to_json(results, callback)
    find_path.exposed = True

    def similar(self, artist, callback=None,  _=''):
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        if callback:
            cherrypy.response.headers['Content-Type']= 'text/javascript'
        else:
            cherrypy.response.headers['Content-Type']= 'application/json'

        start_time = time.time()
        results = {}
        seed, sims = graph.sim_artist(artist)
        if sims:
            results['status'] = 'ok'
            results['seed'] = graph.get_artist(seed)
            results['sims'] = [graph.get_artist(id) for id in sims]
        else:
            results['status'] = 'error'
        results['time'] = time.time() - start_time
        return to_json(results, callback)
    similar.exposed = True

    def random(self, callback=None,  _=''):
        cherrypy.response.headers["Access-Control-Allow-Origin"] = "*"
        if callback:
            cherrypy.response.headers['Content-Type']= 'text/javascript'
        else:
            cherrypy.response.headers['Content-Type']= 'application/json'

        results = graph.get_random_artist()
        return to_json(results, callback)
    random.exposed = True



def make_list(item):
    if item and not isinstance(item, list):
        item = [ item ]
    return item

def to_json(dict, callback=None):
    results =  json.dumps(dict, sort_keys=True, indent = 4) 
    if callback:
        results = callback + "(" + results + ")"
    return results

if __name__ == '__main__':
    urllib2.install_opener(urllib2.build_opener())
    conf_path = os.path.abspath('web.conf')
    print 'reading config from', conf_path
    cherrypy.config.update(conf_path)

    config = ConfigParser.ConfigParser()
    config.read(conf_path)
    production_mode = config.getboolean('settings', 'production')

    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Set up site-wide config first so we get a log if errors occur.

    if production_mode:
        print "Starting in production mode"
        cherrypy.config.update({'environment': 'production',
                                'log.error_file': 'simdemo.log',
                                'log.screen': True})
    else:
        print "Starting in development mode"
        cherrypy.config.update({'noenvironment': 'production',
                                'log.error_file': 'site.log',
                                'log.screen': True})

    conf = webtools.get_export_map_for_directory("static")
    cherrypy.quickstart(ArtistGraphServer(config), '/ArtistGraphServer', config=conf)

