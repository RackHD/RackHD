"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import unittest


class TestLoggerStdoutNoError(unittest.TestCase):
    # should not see anything from this class.
    def setUp(self):
        print "STDOUT-MATCH-DATA: {0} setUp".format(self.__class__.__name__)
        super(TestLoggerStdoutNoError, self).setUp()

    def test_stdout_from_testcase(self):
        print "STDOUT-MATCH-DATA: {0} test_stdout_from_testcase".format(self.__class__.__name__)
