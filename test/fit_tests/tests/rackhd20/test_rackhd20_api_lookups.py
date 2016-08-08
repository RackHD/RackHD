'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/common")
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_lookups(fit_common.unittest.TestCase):
    def setUp(self):
        # delete any instance of test lookup
        api_data = fit_common.rackhdapi("/api/2.0/lookups")
        for item in api_data['json']:
            if item['macAddress'] == "00:0a:0a:0a:0a:0a":
                fit_common.rackhdapi("/api/2.0/lookups/" + item['id'], action="delete")

    def test_api_20_lookups_ID(self):
        api_data = fit_common.rackhdapi("/api/2.0/lookups")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            self.assertEqual(fit_common.rackhdapi("/api/2.0/lookups/" + item['id'])
                             ['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    # this test cross-references node MAC addresses to lookup tables
    def test_api_20_lookups_cross_reference(self):
        nodecatalog = fit_common.rackhdapi("/api/2.0/nodes")['json']
        lookuptable = fit_common.rackhdapi("/api/2.0/lookups")['json']
        errorlist = ""
        for node in nodecatalog:
            # get list of compute nodes with sku
            if node['type'] == "compute" and 'sku' in node and 'identifiers' in node:
                # find node entry mac addresses
                for macaddr in node['identifiers']:
                    # find mac address in lookup table
                    for lookupid in lookuptable:
                        #verify node ID for mac address
                        if macaddr in lookupid['macAddress']:
                            if fit_common.VERBOSITY >= 2:
                                print "*** Checking Node ID: " + node['id'] + "   MAC: " + macaddr
                            if 'node' not in lookupid:
                                errorlist = errorlist + "Missing node ID: " +  node['id'] + "   MAC: " + macaddr + "\n"
                            if node['id'] != lookupid['node']:
                                errorlist = errorlist + "Wrong node in lookup table ID: " +  lookupid['id'] + "\n"
        if errorlist != "":
            print "**** Lookup Errors:"
            print errorlist
        self.assertEqual(errorlist, "", "Errors in lookup table detected.")

    def test_api_20_lookups_post_get_delete(self):
        node = fit_common.node_select()[0]
        data_payload = {
            "macAddress": "00:0a:0a:0a:0a:0a",
            "ipAddress": "128.128.128.128",
            "node": node
        }
        api_data = fit_common.rackhdapi("/api/2.0/lookups", action="post", payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        lookup_id = api_data['json']['id']
        api_data = fit_common.rackhdapi("/api/2.0/lookups/" + lookup_id)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertEqual(api_data['json']['macAddress'], "00:0a:0a:0a:0a:0a", "Bad lookup MAC Address")
        self.assertEqual(api_data['json']['ipAddress'], "128.128.128.128", "Bad lookup IP Address")
        self.assertEqual(api_data['json']['node'], node, "Bad lookup node ID")
        api_data = fit_common.rackhdapi("/api/2.0/lookups/" + lookup_id, action="delete")
        self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
