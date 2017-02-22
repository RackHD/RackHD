'''
Copyright 2016, EMC, Inc.

Author(s): George Paulos

This tests the API 2.0 query feature
'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess

import fit_common

from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

def query_check(url):
    # Run query for each key in first item, then check to see if number of entries match
    errorcount = 0
    api_data = fit_common.rackhdapi(url)['json']
    for item in dict.keys(api_data[0]):
        if type(api_data[0][item]) is not list \
                and type(api_data[0][item]) is not dict\
                and 'api/2.0' not in api_data[0][item]:
            query_data = fit_common.rackhdapi(url + '?' + item + '=' + str(api_data[0][item]))
            for block in query_data['json']:
                if str(block[item]) !=  str(api_data[0][item]):
                    print "Query failure on:" + str(block[item])
                    errorcount += 1
    return errorcount

class rackhd20_query(fit_common.unittest.TestCase):

    def test_catalogs(self):
        self.assertEqual(query_check('/api/2.0/catalogs'), 0, 'Query failed catalogs')

if __name__ == '__main__':
    fit_common.unittest.main()
