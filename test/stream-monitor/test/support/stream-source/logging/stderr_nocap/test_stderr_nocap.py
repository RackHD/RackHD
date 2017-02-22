"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import unittest


class TestLoggerStderrNoError(unittest.TestCase):
    # should not see anything from this class.
    def setUp(self):
        print "STDERR-MATCH-DATA: {0} setUp".format(self.__class__.__name__)
        super(TestLoggerStderrNoError, self).setUp()

    def test_stderr_from_testcase(self):
        print "STDERR-MATCH-DATA: {0} test_stderr_from_testcase".format(self.__class__.__name__)
