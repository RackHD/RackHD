'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
import fit_path
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class redfish10_api_control(fit_common.unittest.TestCase):
    def test_redfish_v1_registries(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Registries')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        # iterate through links
        for item in api_data['json']['Members']:
            self.assertEqual(fit_common.rackhdapi(item['@odata.id'])['status'], 200, "Bad or missing link: " + item['@odata.id'])

    def test_redfish_v1_registries_en(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Registries')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        for item in api_data['json']['Members']:
            registry_data = fit_common.rackhdapi('/redfish/v1/Registries/en/' + item['@odata.id'].replace('/redfish/v1/Registries/', ''))
            self.assertEqual(registry_data['status'], 200, "Was expecting code 200. Got " + str(registry_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
