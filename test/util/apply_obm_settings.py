'''
Copyright 2017, Dell EMC

Author(s):
George Paulos

Script to apply OBM settings to all or selected nodes using BMC credentials in credentials_default.json

Nodes or SKUs can be selected by using the '-sku' or '-nodeid' arguments at command line

'''

import os
import sys
import subprocess


sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common


from nose.plugins.attrib import attr
@attr(all=True)


class apply_obm_settings(fit_common.unittest.TestCase):

    def test_apply_obm_settings(self):
       self.assertTrue(fit_common.apply_obm_settings(), "OBM settings failed.")

if __name__ == '__main__':
    fit_common.unittest.main()
