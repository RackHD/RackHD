"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import unittest
from logging import getLogger


class TestLoggerBacktrace(unittest.TestCase):
    def setUp(self):
        self.__lg = getLogger('infra.run')
        super(TestLoggerBacktrace, self).setUp()

    def test_backtrace_from_oops(self):
        # the next statement will fail because "i_dont_exist" does not exist :)
        # the trailing comment makes it so flake doesn't error on it like it should.
        _ = i_dont_exist  # noqa: F841,F821
