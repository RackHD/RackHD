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
class rackhd11_api_obms(fit_common.unittest.TestCase):
    def test_api_11_obms_library_duplicates(self):
        api_data = fit_common.rackhdapi("/api/1.1/obms/library")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item['service']
            self.assertGreater(len(item['service']), 0, 'service field error')
        # duplicate check
        nodelist = api_data['json']
        for nodenum in range(1, len(api_data['json'])):
            # obm service name
            for nodecheck in range(0, len(api_data['json'])):
                if nodenum != nodecheck:
                    self.assertNotEqual(nodelist[nodenum]['service'],
                                        nodelist[nodecheck]['service'],
                                        "Duplicate service " + nodelist[nodenum]['service'])

    def test_api_11_obms_library(self):
        api_data = fit_common.rackhdapi("/api/1.1/obms/library")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            obm_data = fit_common.rackhdapi("/api/1.1/obms/library/" + item['service'])
            self.assertEqual(obm_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            self.assertGreater(len(obm_data['json']['service']), 0, 'service field error')

if __name__ == '__main__':
    fit_common.unittest.main()

