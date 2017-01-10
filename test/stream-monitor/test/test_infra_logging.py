"""
Copyright 2016, EMC, Inc.

This file contains (very very crude, at the moment!) self
tests of the logging infrastructure.
"""
import flogging
import os
from unittest import TestCase

class TestInfraLogging(TestCase):
    def test_canary(self):
        """canary test to make sure tests are being picked up"""
        pass

    def setUp(self):
        self.__lg_full_path = flogging.logger_get_logging_dir()
        self.__lg_container_path = os.path.dirname(self.__lg_full_path)
        self.__lg_sym_path = os.path.join(self.__lg_container_path, 'run_last.d')

    def test_symlink_exists(self):
        """test run_last.d symlink exists"""
        # lexists returns True for anything that exists (even a broken link)
        self.assertTrue(os.path.lexists(self.__lg_sym_path),
                        "'{0}' does not exist on filesystem".format(self.__lg_sym_path))
        # the next check weeds outs out non-links as bad
        self.assertTrue(os.path.islink(self.__lg_sym_path),
                        "'{0}' exists but is not a link".format(self.__lg_sym_path))
        # and finally, use .exists, which is like lexists except that it returns False for
        # broken links.
        self.assertTrue(os.path.exists(self.__lg_sym_path),
                        "'{0}' is a link that exists, but what it points to does not exist".format(self.__lg_sym_path))


    def test_symlink_is_relative(self):
        """test run_last.d symlink is relative and not absolute"""
        # note test_symlink_exists probes all forms of existence
        sym_target = os.readlink(self.__lg_sym_path)
        self.assertFalse(sym_target.startswith('/'),
                         "'{0}'->'{1}' is an absolute path and must be relative".format(
                             self.__lg_sym_path, sym_target))
