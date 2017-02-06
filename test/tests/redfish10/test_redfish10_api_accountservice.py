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

class redfish10_api_accountservice(fit_common.unittest.TestCase):
    def test_redfish_v1_accountservice(self):
        api_data = fit_common.rackhdapi('/redfish/v1/AccountService')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))

    def test_redfish_v1_accountservice_roles(self):
        api_data = fit_common.rackhdapi('/redfish/v1/AccountService/Roles')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        #iterate through member links
        for item in api_data['json']['Members']:
            link_data = fit_common.rackhdapi(item['@odata.id'])
            self.assertEqual(link_data['status'], 200, "Was expecting code 200. Got " + str(link_data['status']))

    def test_redfish_v1_accountservice_accounts(self):
        api_data = fit_common.rackhdapi('/redfish/v1/AccountService/Accounts')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        #iterate through member links
        for item in api_data['json']['Members']:
            link_data = fit_common.rackhdapi(item['@odata.id'])
            self.assertEqual(link_data['status'], 200, "Was expecting code 200. Got " + str(link_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
