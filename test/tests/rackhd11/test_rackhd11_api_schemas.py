'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr


@attr(api_1_1=True)
class rackhd11_api_schemas(fit_common.unittest.TestCase):
    def test_api_11_schemas(self):
        api_data = fit_common.rackhdapi("/api/1.1/schemas")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
             if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['id']
             self.assertEqual(fit_common.rackhdapi("/api/1.1/schemas/" + item['id'])
                             ['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()

