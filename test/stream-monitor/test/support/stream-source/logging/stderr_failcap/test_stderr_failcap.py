"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import unittest
import sys


class TestLoggerStderrFail(unittest.TestCase):
    def setUp(self):
        print >>sys.stderr, "STDERR-MATCH-DATA: {0} setUp".format(self.__class__.__name__)
        super(TestLoggerStderrFail, self).setUp()

    def test_stderr_from_testcase(self):
        print >>sys.stderr, "STDERR-MATCH-DATA: {0} test_stderr_from_testcase".format(self.__class__.__name__)
        self.assertTrue(False, "failed test to check against")

    def test_no_stderr_from_testcase(self):
        print >>sys.stderr, "STDERR-MUST-NOT-SEE: {0} test_no_stderr_from_testcase".format(self.__class__.__name__)
