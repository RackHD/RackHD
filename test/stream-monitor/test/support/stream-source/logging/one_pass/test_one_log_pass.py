import unittest
from logging import getLogger

class TestOneLoggerTest(unittest.TestCase):
    def setUp(self):
        self.__lg = getLogger('infra.run')
        super(TestOneLoggerTest, self).setUp()

    def test_single_log_to_run(self):
        self.__lg.warning('test_single_log_to_run')
