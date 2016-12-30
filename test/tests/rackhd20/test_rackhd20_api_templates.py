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
class rackhd20_api_templates(fit_common.unittest.TestCase):
    def setUp(self):
        # this clears out any existing instance of 'testid' template
        fit_common.rackhdapi("/api/2.0/templates/library/testid", action="delete")

    def test_api_20_templates_metadata(self):
        api_data = fit_common.rackhdapi("/api/2.0/templates/metadata")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        for item in api_data['json']:
            # check required fields
            for subitem in ['hash', 'id', 'name', 'scope']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['name'], subitem
                self.assertGreater(len(item[subitem]), 0, subitem + ' field error')

    def test_api_20_templates_metadata_ID(self):
        api_data = fit_common.rackhdapi("/api/2.0/templates/metadata")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        for item in api_data['json']:
            lib_data = fit_common.rackhdapi("/api/2.0/templates/metadata/" + item['name'])
            self.assertEqual(lib_data['status'], 200, "Was expecting code 200. Got " + str(lib_data['status']))
            # check required fields
            for subitem in ['hash', 'id', 'name', 'scope']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['name'], subitem
                self.assertGreater(len(item[subitem]), 0, subitem + ' field error')

    def test_api_20_templates_library_ID_put_get_delete(self):
        # this test creates a dummy template called 'testid', checks it, then deletes it
        api_data = fit_common.rackhdapi("/api/2.0/templates/library/testid?scope=global", action="text-put", payload="null")
        self.assertEqual(api_data['status'], 201, "Was expecting code 201. Got " + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/2.0/templates/library/testid")
        self.assertEqual(api_data['text'], "null", "Data 'null' was not returned.")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/2.0/templates/library/testid", action="delete")
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
