'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_users(fit_common.unittest.TestCase):
    def test_api_20_users_get(self):
        api_data = fit_common.rackhdapi('/api/2.0/users')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_api_20_users_post_get_delete(self):
        # test incomplete, needs authorization code
        payload = {
                      "username": "readonly",
                      "password": "1234567",
                      "role": "ReadOnly"
                    }
        api_data = fit_common.rackhdapi('/api/2.0/users', action="post", payload=payload)
        self.assertIn(api_data['status'], [201, 401], 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi('/api/2.0/users')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi('/api/2.0/users/readonly', action="delete")
        self.assertIn(api_data['status'], [204, 404], 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
