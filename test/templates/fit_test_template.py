'''
Copyright 2017, Dell Emc

Author(s):

FIT test script template

Test Script summary:
This template contains the basic script layout for functional test scripts.
It includes examples of using the fit_common methods rackhdapi() to make RackHD API calls.
It also shows an example of using the unittest class method.
It also shows examples of using dependencies between tests with nosedep.
'''

import sys
import subprocess
import unittest
from json import dumps

# import nose decorator attr
from nose.plugins.attrib import attr

# Import nosedep if dependencies are needed between tests
from nosedep import depends

# Import the logging feature
import flogging

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test")
from common import fit_common

# set up the logging
logs = flogging.get_loggers()

# Define the test group here using unittest @attr
# @attr is a decorator and must be located in the line just above the class to be labeled
#   These can be any label to run groups of tests selectively
#   When setting regression or smoke to True, the test must meet CI requirements


@attr(regression=False, smoke=False, my_tests_group=True)
class fit_template(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # class method is run once per script
        # usually not required in the script
        cls.nodes = []

    def setUp(self):
        # setUp is run for each test
        logs.info("  **** Running test: %s", self._testMethodName)

    def shortDescription(self):
        # This removes the docstrings (""") from the unittest test list (collect-only)
        return None

    def my_utility(self):
        # local script method
        return None

    def test_first(self):
        """ Test 1: This test shows success """
        logs.info("This is a successful test")
        logs.debug("This is debug info for successful test")
        self.assertEqual(0, 0)

    @depends(after=test_first)
    def test_second_expect_fail(self):
        """ Test: This test shows failed """
        logs.error(" This is a failed test")
        logs.debug_1(" This is debug info at level 1")
        self.assertEqual(1, 0, msg=("failure due to force assert"))

    def test_next(self):
        """ Test: This test verifies no dependecy chain """
        logs.info_5(" This is a successful test")
        self.assertEqual(0, 0)

    @depends(after=[test_first, test_next])
    def test_next_next(self):
        """ Test: This test depends on two tests to pass """
        logs.warning(" This is a passed test")
        self.assertNotEqual(1, 0, msg="good error message")

    @depends(after=test_second_expect_fail)
    def test_this_will_get_skipped(self):
        """ Test: This test depends a test that will fail """
        logs.info(" This will not get printed")
        self.assertEqual(0, 0)

    @depends(after=test_first)
    def test_get_nodes(self):
        """
        This test is an example of using fit_common.node_select to retrieve a node list.
        For demo purposes, it needs communication to a running rackhd instance or will fail.
        """
        nodes = []
        # Retrive list of nodes, default gets compute nodes
        nodes = fit_common.node_select()

        # Check if any nodes returned
        self.assertNotEqual([], nodes, msg=("No Nodes in List"))

        # Log the list of nodes
        logs.info(" %s", dumps(nodes, indent=4))

    @depends(after=test_get_nodes)
    def test_get_nodes_rackhdapi(self):
        """
        This test is an example of using fit_common.rackhdapi() to perform an API call
        and using data from the response.
        For demo purposes, it needs communication to a running rackhd instance.
        """
        nodes = []
        nodelist = []

        # Perform an API call
        api_data = fit_common.rackhdapi('/api/2.0/nodes')

        # Check return status is what you expect
        status = api_data.get('status')
        self.assertEqual(status, 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # Use the response data
        try:
            nodes = api_data.get('json')
        except:
            self.fail("No Json data in repsonse")
        for node in nodes:
            nodelist.append(node.get('id'))
        logs.info(" %s", dumps(nodelist, indent=4))

        # example to set the class level nodelist
        self.__class__.nodes = nodelist

    @depends(after=test_get_nodes_rackhdapi)
    def test_display_class_nodes(self):
        """
        This test is an example of using the class variable 'nodes'
        The prior test set the class variable to be used by this test.
        This test prints out the class variable
        """
        my_nodes = self.__class__.nodes
        logs.info(" %s", dumps(my_nodes, indent=4))


if __name__ == '__main__':
    unittest.main()
