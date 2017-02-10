"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import unittest
from logging import getLogger


class TestTwoLoggerTest(unittest.TestCase):
    def setUp(self):
        self.__lg = getLogger('infra.run')
        super(TestTwoLoggerTest, self).setUp()

    def test_one_of_two_to_run(self):
        self.__lg.warning('test_one_of_two_to_run')

    def test_two_of_two_to_run(self):
        self.__lg.warning('test_two_of_two_to_run')
