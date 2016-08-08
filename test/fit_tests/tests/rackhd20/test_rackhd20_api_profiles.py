'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_profiles(fit_common.unittest.TestCase):
    def test_api_20_profiles_library(self):
        api_data = fit_common.rackhdapi("/api/2.0/profiles")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            # check required fields
            for subitem in ['contents', 'createdAt', 'id', 'name', 'updatedAt']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", str(item['name']), subitem
                self.assertGreater(len(str(item[subitem])), 0, subitem + ' field error')

if __name__ == '__main__':
    fit_common.unittest.main()
