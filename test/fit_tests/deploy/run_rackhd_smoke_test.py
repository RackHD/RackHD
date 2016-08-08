'''
Copyright 2015, EMC, Inc.

Author(s):
George Paulos

This wrapper script installs RackHD and runs Smoke Test.
'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/common")
import fit_common

class rackhd_smoke_test(fit_common.unittest.TestCase):
    def test01_install_os_ova(self):
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/deploy/os_ova_install.py'), 0, 'OS installer failed.')

    def test02_rackhd_installer(self):
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/deploy/rackhd_source_install.py'), 0, 'RackHD source installer failed.')

    def test03_initialize_stack(self):
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/deploy/rackhd_stack_init.py'), 0, 'RackHD stack init failed.')

    def test04_rackhd_smoke_test(self):
        # set test group to 'smoke'
        fit_common.ARGS_LIST['group'] = "smoke"
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/tests'), 0, 'RackHD Smoke Test failed.')

if __name__ == '__main__':
    fit_common.unittest.main()