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
class rackhd11_api_config(fit_common.unittest.TestCase):
    def test_api_11_config(self):
        api_data = fit_common.rackhdapi('/api/1.1/config')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        # check required fields
        self.assertIn('PATH', api_data['json'], 'PATH field error')
        self.assertIn('amqp', api_data['json'], 'amqp field error')
        self.assertIn('apiServerAddress', api_data['json'], 'apiServerAddress field error')
        self.assertIn('apiServerPort', api_data['json'], 'apiServerPort field error')
        self.assertIn('broadcastaddr', api_data['json'], 'broadcastaddr field error')
        self.assertIn('CIDRNet', api_data['json'], 'CIDRNet field error')
        self.assertIn('subnetmask', api_data['json'], 'subnetmask field error')
        self.assertIn('mongo', api_data['json'], 'mongo field error')

    def test_api_11_config_httpendpoints(self):
        api_data = fit_common.rackhdapi('/api/1.1/config')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        self.assertIn('httpEndpoints', api_data['json'], 'httpEndpoints field list error')
        # verify both northbound and southbound endpoints are configured (as a minimum)
        for endpoint in api_data['json']['httpEndpoints']:
            self.assertIn('address', endpoint, 'missing httpEndpoints address field')
            self.assertIn('authEnabled', endpoint, 'missing httpEndpoints authEnabled field')
            self.assertIn('httpsEnabled', endpoint, 'missing httpEndpoints httpsEnabled field')
            self.assertIn('proxiesEnabled', endpoint, 'missing httpEndpoints proxiesEnabled field')
            self.assertIn('routers', endpoint, 'missing httpEndpoints routers field')
            self.assertIn(endpoint['routers'], ['northbound-api-router', 'southbound-api-router'], 'unexpected httpEndpoints routers field')

    def test_api_11_config_patch(self):
        api_data_save = fit_common.rackhdapi('/api/1.1/config')['json']
        data_payload = {"CIDRNet": "127.0.0.1/22"}
        api_data = fit_common.rackhdapi("/api/1.1/config", action="patch", payload=data_payload)
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item
            self.assertNotEqual(item, '', 'Empty JSON Field:' + item)
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/1.1/config", action="patch", payload=api_data_save)
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        api_data = fit_common.rackhdapi('/api/1.1/config')
        self.assertEqual(api_data['json'], api_data_save)

if __name__ == '__main__':
    fit_common.unittest.main()
