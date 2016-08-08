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
class rackhd11_api_misc(fit_common.unittest.TestCase):
    def test_api_11_docs_page(self):
        api_data = fit_common.rackhdapi('/docs')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertIn('html', api_data['text'], 'Missing HTML header')

    def test_api_11_versions(self):
        api_data = fit_common.rackhdapi("/api/1.1/versions")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print item['package'], item['version']
            self.assertGreater(len(item['package']), 0, 'package field error')
            self.assertGreater(len(item['version']), 0, 'version field error')

if __name__ == '__main__':
    fit_common.unittest.main()
