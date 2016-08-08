'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/common")
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class redfish10_api_sessionservice(fit_common.unittest.TestCase):
    def test_redfish_v1_sessionservice(self):
        api_data = fit_common.rackhdapi('/redfish/v1/SessionService')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))

    def test_redfish_v1_sessionservice_sessions(self):
        api_data = fit_common.rackhdapi('/redfish/v1/SessionService/Sessions')
        self.assertIn(api_data['status'], [200, 501], "Incorrect HTTP return code")

if __name__ == '__main__':
    fit_common.unittest.main()
