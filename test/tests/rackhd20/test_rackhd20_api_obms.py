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
@attr(all=True, regression=True, smoke=True)

class rackhd20_api_obms(fit_common.unittest.TestCase):
    def test_api_20_obms(self):
        api_data = fit_common.rackhdapi("/api/2.0/obms")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            # check fields
            for block in item:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", block
                self.assertGreater(len(str(item[block])), 0, 'Field error: ' + block)

    def test_api_20_obms_definitions(self):
        api_data = fit_common.rackhdapi("/api/2.0/obms/definitions")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # check links
        for item in api_data['json']:
            self.assertEqual(fit_common.rackhdapi(item)['status'], 200, 'Bad link: ' + item)

if __name__ == '__main__':
    fit_common.unittest.main()
