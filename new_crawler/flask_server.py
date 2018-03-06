""" the http server for SFC
"""
import sys
import logging
import atexit
import time

from flask import Flask, request, jsonify
from flask_cors import cross_origin
from werkzeug.contrib.fixers import ProxyFix
import artist_graph

APP = Flask(__name__)
APP.debug = False
APP.trace = False
APP.testing = False
APP.ag = artist_graph.ArtistGraph()

@APP.route('/frog/path')
@cross_origin()
def api_path():
    start = time.time()
    src = request.args.get("src", None)
    dest = request.args.get("dest", None)
    skips = request.args.get("skips", None)

    if skips and len(skips) > 0:
        skipset = set(skips.split(','))
    else:
        skipset = set()

    if src and dest:
        results = APP.ag.path(src, dest, skipset)
    else:
        results = {
            "status": "error",
            "reason": "missing src and/or dest",
        }
    return jsonify(results)


@APP.route('/frog/get')
@cross_origin()
def api_get():
    """ get artist info for the given aids/uris
    """
    start = time.time()
    aids = request.args.get("aids", None)

    if aids and len(aids) > 0:
        artist_ids = aids.split(',')
        out = []
        for artist_id in artist_ids:
            artist = APP.ag.get_artist(artist_id)
            out.append(artist)

        results = {
            "status": "ok",
            "artists": out
        }
    else:
        results = {
            "status": "error",
            "reason": "no input artist ids given"
        }

    fdelta = time.time() - start
    results['fdelta'] = fdelta
    return jsonify(results)

@APP.route('/frog/sims')
@cross_origin()
def api_sims():
    """ get sim artists for the given aid
    """
    start = time.time()
    name = request.args.get("artist", None)

    aid = APP.ag.search(name)

    out = []
    if aid:
        artist = APP.ag.get_artist(aid)
        for edge in artist["edges"]:
            out.append(APP.ag.get_artist(edge))

        results = {
            "status": "ok",
            "sims": out
        }
    else:
        results = {
            "status": "error",
            "reason": "can't find artist " + name
        }

    fdelta = time.time() - start
    results['fdelta'] = fdelta
    return jsonify(results)


#@APP.errorhandler(Exception)
def handle_invalid_usage(error):
    """ implements the standard error processing
    """
    print "error", error
    results = {'status': 'internal_error', "message": str(error)}
    return jsonify(results)


APP.wsgi_app = ProxyFix(APP.wsgi_app)


    
def shutdown():
    """ performs any server shutdown cleanup
    """
    print 'shutting down server ...'
    print 'done'


if __name__ == '__main__':
    APP.debug = False
    APP.trace = False
    APP.wsgi = False
    HOST = '0.0.0.0'
    PORT = 3457  # debugging
    PORT = 4682

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s')

    atexit.register(shutdown)

    for arg in sys.argv[1:]:
        if arg == '--debug':
            APP.debug = True
        if arg == '--trace':
            APP.trace = True
    if APP.debug:
        print 'debug  mode', 'host', HOST, 'port', PORT
        APP.run(threaded=False, debug=True, host=HOST, port=PORT)
    elif APP.wsgi:
        from gevent.wsgi import WSGIServer
        print 'WSGI production  mode', 'port', PORT
        print 'WSGI production mode - ready'
        HTTP_SERVER = WSGIServer(('', PORT), APP)
        HTTP_SERVER.serve_forever()
    else:
        print 'production  mode', 'port/host', PORT, HOST
        print 'production mode - ready'
        APP.run(threaded=True, debug=False, host=HOST, port=PORT)
