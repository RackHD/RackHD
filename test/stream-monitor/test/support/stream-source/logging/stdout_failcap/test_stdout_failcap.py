import unittest

class TestLoggerStdoutFail(unittest.TestCase):
    def setUp(self):
        print "STDOUT-MATCH-DATA: {0} setUp".format(self.__class__.__name__)
        super(TestLoggerStdoutFail, self).setUp()

    def test_stdout_from_testcase(self):
        print "STDOUT-MATCH-DATA: {0} test_stdout_from_testcase".format(self.__class__.__name__)
        self.assertTrue(False, "failed test to check against")

    def test_no_stdout_from_testcase(self):
        print "STDOUT-MUST-NOT-SEE: {0} test_no_stdout_from_testcase".format(self.__class__.__name__)

