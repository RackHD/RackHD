'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common


# Local methods
NODECATALOG = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class redfish10_api_chassis(fit_common.unittest.TestCase):
    def test_redfish_v1_chassis_links(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Chassis')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print ("Checking: {0}".format(item))
            self.assertNotEqual(item, "", 'Empty JSON Field')
        # test all href member links
        for item in api_data['json']['Members']:
            link_data = fit_common.rackhdapi(item['@odata.id'])
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_redfish_v1_chassis_id_links(self):
        #iterate through pre-qualified chassis
        api_data = fit_common.rackhdapi('/redfish/v1/Chassis')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code')
        for nodeid in api_data['json']['Members']:
            api_data = fit_common.rackhdapi(nodeid['@odata.id'])
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            # check required fields
            # check Name field first because that will be used for other checks
            self.assertIn('Name', api_data['json'], 'Name field not present')
            self.assertGreater(len(api_data['json']['Name']), 0, 'Name field empty')
            chassis_name = api_data['json']['Name']

            for item in ['Links', '@odata.id', '@odata.type']:
                if fit_common.VERBOSITY >= 2:
                    print ("Checking: {0}".format(item))
                self.assertIn(item, api_data['json'], item + ' field not present')
                # if the chassis name is Unknown, fields will not be populated
                if chassis_name != 'Unknown':
                    if fit_common.VERBOSITY >= 2:
                        print ("Chassis_name : {0}".format(chassis_name))
                        print ("Checking: {0}".format(item))
                    self.assertGreater(len(api_data['json'][item]), 0, item + ' field empty')

    def test_redfish_v1_chassis_id_power(self):
        #iterate through pre-qualified chassis
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/redfish/v1/Chassis/" + nodeid + "/Power")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            # check required fields
            for item in ['@odata.id', '@odata.type', 'Id']:
                if fit_common.VERBOSITY >= 2:
                    print ("Checking: {0}".format(item))
                self.assertIn(item, api_data['json'], item + ' field not present')
                if fit_common.VERBOSITY >= 3:
                    print ("\t {0}".format( api_data['json'][item]))
                self.assertGreater(len(api_data['json'][item]), 0, item + ' field empty' )

    def test_redfish_v1_chassis_id_thermal(self):
        #iterate through pre-qualified chassis
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Chassis/' + nodeid + '/Thermal')
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for item in ['@odata.type', '@odata.id', 'Id']:
                if fit_common.VERBOSITY >= 2:
                    print ("Checking: {0}".format(item))
                self.assertIn(item, api_data['json'], item + ' field not present')
                if fit_common.VERBOSITY >= 3:
                    print ("\t {0}".format( api_data['json'][item]))
                self.assertGreater(len(api_data['json'][item]), 0, item + ' field empty')

if __name__ == '__main__':
    fit_common.unittest.main()
