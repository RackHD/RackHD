'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import fit_path  # NOQA: unused import
import unittest
import fit_common
import flogging

# set up the logging
logs = flogging.get_loggers()

# Select test group here using @attr
from nose.plugins.attrib import attr


@attr(all=True, regression=True, smoke=True)
class eh_fake_check(unittest.TestCase):
    def test_api_20_EH_NODES(self):
        logs.info("Fail this test")
        api_data = fit_common.rackhdapi('/api/2.0/eh/nodes')
        self.assertEqual(api_data['status'], 200, 'Should FAIL test one')

    def test_api_20_EH_NODES_2(self):
        logs.info("Fail this test again")
        api_data = fit_common.rackhdapi('/api/2.0/eh/nodes/abcd')
        self.assertEqual(api_data['status'], 200, 'Should FAIL test two')

if __name__ == '__main__':
    fit_common.unittest.main()
