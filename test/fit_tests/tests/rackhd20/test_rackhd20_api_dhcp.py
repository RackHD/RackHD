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

# Local methods
NODECATALOG = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_dhcp(fit_common.unittest.TestCase):
    def test_api_20_dhcp_get(self):
        # currently not implemented
        api_data = fit_common.rackhdapi('/api/2.0/dhcp')
        self.assertIn(api_data['status'], [200, 404, 501], 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_api_20_dhcp_lease_get(self):
        # currently not implemented
        for item in NODECATALOG:
            node_data = fit_common.rackhdapi('/api/2.0/nodes/' + item)['json']
            api_data = fit_common.rackhdapi('/api/2.0/dhcp/lease/' + str(node_data['name']))
            self.assertIn(api_data['status'], [200, 404, 501], 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
