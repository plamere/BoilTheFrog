# -*- coding: utf-8 -*-
# This Python file uses the following encoding: utf-8
import bisect
import collections
import re
import stringutils
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

client_credentials_manager = SpotifyClientCredentials()
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


class Searcher:

    def __init__(self, exact=False):
        self.items = collections.defaultdict(list)
        self.names = []
        self.exact = exact

    def add(self, name, o):
        # print 'adding', name, o
        s = de_norm(name)
        if o not in self.items[s]:
            self.items[s].append(o)
            bisect.insort_left(self.names, s)

    def search(self, s, force_exact=False):
        exact = self.exact or force_exact

        org_name = s
        s = de_norm(s)
        p = bisect.bisect_left(self.names, de_norm(s))

        matches = []
        for i in xrange(p, len(self.names)):
            if exact and self.names[i] == s:
                matches.append( (len(self.names[i]) - len(s), self.names[i]) )
            elif not exact and  self.names[i].startswith(s):
                matches.append( (len(self.names[i]) - len(s), self.names[i]) )
            else:
                break

        matches.sort()
        results = []

        # TODO: don't add dups
        for l, name in matches:
            for o in self.items[name]:
                results.append(o)
        if len(results) == 0:
            print 'ssearch', s
            sresults = spotify.search(q=s, type='artist')
            for item in sresults['artists']['items']:
                aid = item['id']
                print '  ss', item['name']
                self.add(org_name, aid)
                self.add(item['name'], aid)
                results.append(aid)
        return results
        

def de_norm(name, space=''):
    ''' Dan Ellis normalization
    '''
    s = name
    s = s.replace("'", "")
    s = s.replace(".", "")
    s = strip_accents(s)
    s = s.lower()
    s = re.sub(r'&', ' and ', s)
    s = re.sub(r'^the ', '', s)
    s = re.sub(r'[\W+]', '_', s)
    s = re.sub(r'_+', '_', s)
    s = s.strip('_')
    s = s.replace('_', space)

    # if we've normalized away everything
    # keep it.
    if len(s) == 0:
        s = name
    return s

def de_equals(n1, n2):
    return n1 == n2 or de_norm(n1) == de_norm(n2)

def de_match(n1, n2):
    if de_equals(n1, n2):
        return True
    else:
        dn1 = de_norm(n1)
        dn2 = de_norm(n2)
        return dn1.find(dn2) >= 0 or dn2.find(dn1) >= 0

def strip_accents(s):
    return stringutils.unaccent(s)

def test_norm(s):
    print s, de_norm(s)

def norm_test():
    test_norm("N'sync")
    test_norm("D'Angelo")
    test_norm("R. Kelly")
    test_norm("P.J. Harvey")
    test_norm("Beyoncé")
    test_norm("The Bangles")
    test_norm("Run-D.M.C.")
    test_norm("The Presidents of the United States of America")
    test_norm("Emerson Lake & Palmer")
    test_norm("Emerson, Lake & Palmer")
    test_norm("Emerson, Lake and Palmer")
    test_norm("Emerson Lake and Palmer")


if __name__ == '__main__':
    norm_test()
