'''
Copyright 2016, EMC, Inc.

Author(s):

FIT test wrapper script template
'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

class wrapper_template(fit_common.unittest.TestCase):
    def test01(self):
        self.assertEqual(fit_common.run_nose('fit_test_template.py'), 0)

if __name__ == '__main__':
    fit_common.unittest.main()
