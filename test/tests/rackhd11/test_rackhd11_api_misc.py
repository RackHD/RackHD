'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(api_1_1=True)
class rackhd11_api_misc(fit_common.unittest.TestCase):
    def test_api_11_docs_page(self):
        api_data = fit_common.rackhdapi('/docs')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertIn('html', api_data['text'], 'Missing HTML header')

if __name__ == '__main__':
    fit_common.unittest.main()
