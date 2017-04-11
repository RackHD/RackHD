"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
from __future__ import print_function
import unittest


class TestLoggerStdoutError(unittest.TestCase):
    def setUp(self):
        print("STDOUT-MATCH-DATA: {0} setUp".format(self.__class__.__name__))
        super(TestLoggerStdoutError, self).setUp()

    def test_stdout_from_testcase(self):
        print("STDOUT-MATCH-DATA: {0} test_stdout_from_testcase".format(self.__class__.__name__))
        raise Exception("error in test rather than fail type thing")

    def test_no_stdout_from_testcase(self):
        print("STDOUT-MUST-NOT-SEE: {0} test_no_stdout_from_testcase".format(self.__class__.__name__))
