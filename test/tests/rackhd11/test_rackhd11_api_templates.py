'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd11_api_templates(fit_common.unittest.TestCase):
    def setUp(self):
        # this clears out any existing instance of 'testid' template
        # template 'delete' not supported in API 1.1, using 2.0
        fit_common.rackhdapi("/api/2.0/templates/library/testid", action="delete")

    def test_api_11_templates_library(self):
        api_data = fit_common.rackhdapi("/api/1.1/templates/library")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        for item in api_data['json']:
            # check required fields
            for subitem in ['contents', 'createdAt', 'id', 'name', 'updatedAt']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['name'], subitem
                self.assertGreater(len(item[subitem]), 0, subitem + ' field error')

    def test_api_11_templates_library_ID_put_get_delete(self):
        # this test creates a dummy template called 'testid', checks it, then deletes it
        api_data = fit_common.rackhdapi("/api/1.1/templates/library/testid?scope=global", action="text-put", payload="null")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/1.1/templates/library/testid")
        self.assertIn(api_data['json']['contents'], "null", "Data 'null' was not returned.")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        # template 'delete' not supported in API 1.1, using 2.0
        api_data = fit_common.rackhdapi("/api/2.0/templates/library/testid", action="delete")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
