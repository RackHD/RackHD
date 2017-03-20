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
import json

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class redfish10_api_chassis(fit_common.unittest.TestCase):
    def test_01_redfish_v1_chassis_links(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Chassis')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print ("Checking: {0}".format(item))
            self.assertNotEqual(item, "", 'Empty JSON Field')
        # test all href member links
        for item in api_data['json']['Members']:
            if fit_common.VERBOSITY >= 2:
                print ("Member: {}".format(item))
            link_data = fit_common.rackhdapi(item['@odata.id'])
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_02_redfish_v1_chassis_id_links(self):
        #iterate through list of chassis from redfish
        api_data = fit_common.rackhdapi('/redfish/v1/Chassis')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code')
        for nodeid in api_data['json']['Members']:
            if fit_common.VERBOSITY >= 2:
                print ("Node ID: {} ".format(nodeid))
            api_data = fit_common.rackhdapi(nodeid['@odata.id'])
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            # check required fields
            # check Name field first because that will be used for other checks
            self.assertIn('Name', api_data['json'], 'Name field not present')
            self.assertGreater(len(api_data['json']['Name']), 0, 'Name field empty')
            chassis_name = api_data['json']['Name']
            if fit_common.VERBOSITY >= 2:
                print ("Node ID: {} Name: {} ".format(nodeid, chassis_name))
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

    def test_03_redfish_v1_chassis_id_power(self):
        errorlist = []
        # Get list of nodes from the redfish Chassis API
        api_data = fit_common.rackhdapi('/redfish/v1/Chassis')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code')
        for nodeid in api_data['json']['Members']:
            powerurl = nodeid['@odata.id'] + "/Power"
            node = nodeid['@odata.id'].split('/')[-1]
            if fit_common.VERBOSITY >= 2:
                print ("Node ID: {} ".format(node))
                print "Power url", powerurl
            api_data = fit_common.rackhdapi(powerurl)
            if api_data['status'] != 200:
                errorlist.append("Nodeid: {} Bad return code {} for url: {}".format(node, api_data['status'], powerurl))
            else:
                # check required fields
                for item in ['@odata.id', '@odata.type', 'Id']:
                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(item))
                    self.assertIn(item, api_data['json'], item + ' field not present')
                    if fit_common.VERBOSITY >= 3:
                        print ("\t {0}".format( api_data['json'][item]))
                    self.assertGreater(len(api_data['json'][item]), 0, item + ' field empty' )
        if errorlist:
            print json.dumps(errorlist, indent=4)
        self.assertEqual(errorlist, [], "Errors found".format(errorlist))

    def test_04_redfish_v1_chassis_id_thermal(self):
        errorlist = []
        # Get list of Chassis from the stack
        api_data = fit_common.rackhdapi('/redfish/v1/Chassis')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code')
        for nodeid in api_data['json']['Members']:
            thermalurl = nodeid['@odata.id'] + "/Thermal"
            node = nodeid['@odata.id'].split('/')[-1]
            if fit_common.VERBOSITY >= 2:
                print ("Node ID: {} ".format(node))
                print "Thermal url", thermalurl
            api_data = fit_common.rackhdapi(thermalurl)
            if api_data['status'] != 200:
                errorlist.append("Nodeid: {} Bad return code {} for url: {}".format(node, api_data['status'], thermalurl))
            else:
                for item in ['@odata.type', '@odata.id', 'Id']:
                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(item))
                    self.assertIn(item, api_data['json'], item + ' field not present')
                    if fit_common.VERBOSITY >= 3:
                        print ("\t {0}".format( api_data['json'][item]))
                    self.assertGreater(len(api_data['json'][item]), 0, item + ' field empty')
        if errorlist:
            print json.dumps(errorlist, indent=4)
        self.assertEqual(errorlist, [], "Errors found".format(errorlist))

if __name__ == '__main__':
    fit_common.unittest.main()
