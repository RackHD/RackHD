'''
Copyright 2016, EMC, Inc.

Author(s):

FIT test script template
'''

import os
import sys
import subprocess

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# Select test group here using @attr, these can be any labels to run groups of tests selectively
# @attr is a decorator and mus be located in the line just above the class to be labeled
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class fit_template(fit_common.unittest.TestCase):

    def setUp(self):
        print "\n**** Running test:", self._testMethodName
        print "----------------------------------------------------------------------\n"

    def test1(self):
        # successful test here
        print "This is a successful test"
        self.assertEqual(0, 0)

    def test2(self):
        # failed test here
        print "This is a failed test"
        self.assertEqual(1, 0)

    def test3(self):
        # failed test here
        print "This is a failed test"
        self.assertNotEqual(0, 0)

if __name__ == '__main__':
    fit_common.unittest.main()
