'''
Copyright 2016, EMC, Inc.

Author(s):

FIT test wrapper script template
'''

import os
import sys
import subprocess
import fit_path
import fit_common

class wrapper_template(fit_common.unittest.TestCase):
    def test01(self):
        self.assertEqual(fit_common.run_nose('fit_test_template.py'), 0)

if __name__ == '__main__':
    fit_common.unittest.main()
