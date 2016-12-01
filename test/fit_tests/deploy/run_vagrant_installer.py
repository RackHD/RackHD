'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

This script installs RackHD via source to Vagrant/Virtualbox deployment
This script performs the following functions:
    - clears out orphan VMs from Virtualbox
    - installs OS template
    - installs RackHD from source
    - installs node simulator
    - installs SKU packs
    - runs stack init

NOTES:
    This script requires Vagrant and Virtualbox installed on the Linux test host.
    Virtualbox must be running under default host user.
    '-stack' parameter must be specified when launching, and selected stack must have 'type':'vagrant'

'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common

# test for Vagrant installation
if subprocess.call('vagrant -v', shell=True) != 0:
    print "**** ERROR: Vagrant not installed, exiting..."
    sys.exit(255)

class vagrant_installer(fit_common.unittest.TestCase):
    def test00_cleanup(self):
        subprocess.call('vagrant destroy -f template', shell=True)
        subprocess.call('vagrant destroy -f quanta_d51', shell=True)

    def test01_install_os(self):
        self.assertEqual(subprocess.call('vagrant up template', shell=True), 0, 'OS installer failed.')

    def test02_rackhd_installer(self):
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/deploy/rackhd_source_install.py'), 0, 'RackHD package installer failed.')

    def test03_initialize_sku(self):
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/deploy/rackhd_stack_init.py:rackhd_stack_init.test01_preload_sku_packs'), 0, 'RackHD SKU install failed.')

    def test04_install_node(self):
        self.assertEqual(subprocess.call('vagrant up quanta_d51', shell=True), 0, 'Node installer failed.')

    def test05_initialize_stack(self):
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/deploy/rackhd_stack_init.py'), 0, 'RackHD stack init failed.')

if __name__ == '__main__':
    fit_common.unittest.main()
