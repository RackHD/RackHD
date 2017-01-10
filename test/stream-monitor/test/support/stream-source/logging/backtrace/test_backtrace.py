import unittest
from logging import getLogger

class TestLoggerBacktrace(unittest.TestCase):
    def setUp(self):
        self.__lg = getLogger('infra.run')
        super(TestLoggerBacktrace, self).setUp()

    def test_backtrace_from_oops(self):
        # the next statement will fail because "i_dont_exist" does not exist :)
        _ = i_dont_exist

