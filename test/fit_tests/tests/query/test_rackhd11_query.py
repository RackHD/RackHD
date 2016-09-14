'''
Copyright 2016, EMC, Inc.

Author(s): George Paulos

This tests the API 1.1 query feature
'''

import os
import sys
import subprocess

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common

from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

def query_check(url):
    # Run query for each key in first item, then check to see if number of entries match
    errorcount = 0
    api_data = fit_common.rackhdapi(url)['json']
    for item in dict.keys(api_data[0]):
        if type(api_data[0][item]) is not list and type(api_data[0][item]) is not dict:
            query_data = fit_common.rackhdapi(url + '?' + item + '=' + str(api_data[0][item]))
            for block in query_data['json']:
                if str(block[item]) !=  str(api_data[0][item]):
                    print "Query failure on:" + str(block[item])
                    errorcount += 1
    return errorcount

class rackhd11_query(fit_common.unittest.TestCase):

    def test_nodes(self):
        self.assertEqual(query_check('/api/1.1/nodes'), 0, 'Query failed nodes')

    def test_skus(self):
        self.assertEqual(query_check('/api/1.1/skus'), 0, 'Query failed skus')

    def test_catalogs(self):
        self.assertEqual(query_check('/api/1.1/catalogs'), 0, 'Query failed catalogs')

    def test_pollers(self):
        self.assertEqual(query_check('/api/1.1/pollers'), 0, 'Query failed pollers')

if __name__ == '__main__':
    fit_common.unittest.main()
