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
class rackhd20_api_skus(fit_common.unittest.TestCase):
    def setUp(self):
        # delete test skus if present
        api_data = fit_common.rackhdapi("/api/2.0/skus")
        for item in api_data['json']:
            if "test" in item['name']:
                fit_common.rackhdapi("/api/2.0/skus/" + item['id'], action="delete")

    def test_api_20_sku(self):
        api_data = fit_common.rackhdapi("/api/2.0/skus")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            self.assertEqual(fit_common.rackhdapi("/api/2.0/skus/" + item['id'])['status'],
                             200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_api_20_sku_post_get_delete(self):
        data_payload = {
                        "name": "test1",
                        "rules": [
                            {
                                "contains": "test",
                                "path": "ohai.dmi.base_board.manufacturer"
                            }
                        ]
                        }
        api_data = fit_common.rackhdapi("/api/2.0/skus", action="post", payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/2.0/skus/" + api_data['json']['id'])
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/2.0/skus/" + api_data['json']['id'],
                                           action="delete")
        self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))

    def test_api_20_sku_post_patch_delete(self):
        data_payload = {
                        "name": "test2",
                        "rules": [
                            {
                                "contains": "test",
                                "path": "ohai.dmi.base_board.manufacturer"
                            }
                        ]
                        }
        api_data = fit_common.rackhdapi("/api/2.0/skus", action="post", payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        patch_payload ={"name": "test3"}
        api_data = fit_common.rackhdapi("/api/2.0/skus/" + api_data['json']['id'], action="patch", payload=patch_payload)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertEqual(api_data['json']['name'], "test3", "SKU patch failed")

if __name__ == '__main__':
    fit_common.unittest.main()
