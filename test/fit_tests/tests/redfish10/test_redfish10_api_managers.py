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

class redfish10_api_managers(fit_common.unittest.TestCase):
    def test_redfish_v1_managers(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Managers')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        #iterate through member links
        for item in api_data['json']['Members']:
            self.assertEqual(fit_common.rackhdapi(item['@odata.id'])['status'], 200, "Bad or missing link: " + item['@odata.id'])

    def test_redfish_v1_managers_rackhd_ethernetinterfaces(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Managers/RackHD/EthernetInterfaces')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        #iterate through member links
        for item in api_data['json']['Members']:
            manager_data = fit_common.rackhdapi(item['@odata.id'])
            self.assertEqual(manager_data['status'], 200, "Was expecting code 200. Got " + str(manager_data['status']))
            # if configured, test IP addresses of each port
            if 'IPv4Addresses' in manager_data['json'] and 'Address' in manager_data['json']['IPv4Addresses']:
                for item in manager_data['json']['IPv4Addresses']:
                    self.assertEqual(fit_common.remote_shell('ping -c 1 ' + item["Address"])['exitcode'], 0, "Manager IP address not found.")

    def test_redfish_v1_managers_rackhd_serialinterfaces(self):
        # not yet implemented
        api_data = fit_common.rackhdapi('/redfish/v1/Managers/RackHD/SerialInterfaces/0')
        self.assertIn(api_data['status'], [200, 501], "Was expecting code 501. Got " + str(api_data['status']))

    def test_redfish_v1_managers_rackhd_virtualmedia(self):
        # not yet implemented
        api_data = fit_common.rackhdapi('/redfish/v1/Managers/RackHD/VirtualMedia/0')
        self.assertIn(api_data['status'], [200, 501], "Was expecting code 501. Got " + str(api_data['status']))

    # need test for 'patch' management server API

if __name__ == '__main__':
    fit_common.unittest.main()
