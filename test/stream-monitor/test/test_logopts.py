"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import plugin_test_helper
import unittest
import logging


class _Expector(object):
    def __init__(self, use_logger, at_level, all_all_at='NOTSET', concap_at='INFO_5', real_at='INFO_5'):
        """
        Simple class to automate some of the compare setups.
        """
        self.at_level = at_level
        self.logger_name = use_logger
        self.expect_for_infra_run = None
        self.expect_for_infra_data = None
        self.expect_for_test_run = None
        self.expect_for_test_data = None
        self.expect_for_console_capture = None
        self.expect_for_all_all = None
        self.expect_for_real = None
        figure_all_all = True
        figure_concap = True
        figure_real = True
        if use_logger == 'infra.run':
            self.expect_for_infra_run = at_level
        elif use_logger == 'infra.data':
            self.expect_for_infra_data = at_level
        elif use_logger == 'test.run':
            self.expect_for_test_run = at_level
        elif use_logger == 'test.data':
            self.expect_for_test_data = at_level
        else:
            figure_all_all = False
            figure_concap = False
            figure_real = False

        if figure_all_all:
            self.expect_for_all_all = all_all_at

        if figure_concap:
            self.expect_for_console_capture = concap_at

        if figure_real:
            self.expect_for_real = real_at


class _OutputScannerBase(plugin_test_helper.resolve_logoutput_scanner_helper_class()):
    """
    Plugin tester instance used for each real test block.
    """
    def __common_test_expected(self, expect_level, emit_level, logger_name, log_file):
        if expect_level is not None:
            exp_levelno = logging.getLevelName(expect_level)
            emit_levelno = logging.getLevelName(emit_level)
            expect_level = max(exp_levelno, emit_levelno)
        self._lgfile_watchers[log_file].check_level_output(
            self, expect_level, logger_name)

    def test_infra_run_expected(self):
        self.__common_test_expected(
            self._expector.expect_for_infra_run, self._expector.at_level,
            self._expector.logger_name, 'infra_run.log')

    def test_infra_data_expected(self):
        self.__common_test_expected(
            self._expector.expect_for_infra_data, self._expector.at_level,
            self._expector.logger_name, 'infra_data.log')

    def test_test_run_expected(self):
        self.__common_test_expected(
            self._expector.expect_for_test_run, self._expector.at_level,
            self._expector.logger_name, 'test_run.log')

    def test_test_data_expected(self):
        self.__common_test_expected(
            self._expector.expect_for_test_data, self._expector.at_level,
            self._expector.logger_name, 'test_data.log')

    def test_all_all_expected(self):
        self.__common_test_expected(
            self._expector.expect_for_all_all, self._expector.at_level,
            self._expector.logger_name, 'all_all.log')

    def test_console_capture_expected(self):
        self.__common_test_expected(
            self._expector.expect_for_console_capture, self._expector.at_level,
            self._expector.logger_name, 'console_capture.log')

    def test_real_console(self):
        self.__common_test_expected(
            self._expector.expect_for_real, self._expector.at_level,
            self._expector.logger_name, 'stderr')

    def makeSuite(self):
        """
        This is a required method for plugin-testing that return a suite of tests
        for this class. Said suite must implement "runTest" (see comment there).
        We also 'publish' this class's expector, so the runTest method can see it.
        """
        expector = self._expector

        class TC(unittest.TestCase):
            def runTest(self):
                """
                This method spams the logger from the expector from its base level
                up to CRITICAL with a message that is fairly easy to regex match in
                the routines from the methods in test_log_stream.py.
                """
                import logging
                lg_name = expector.logger_name
                lg = logging.getLogger(lg_name)
                start_level = logging.getLevelName('DEBUG_9')
                end_level = logging.getLevelName('CRITICAL_0')
                for lvl in range(start_level, end_level):
                    lg.log(lvl, 'MATCH-START %s %d(%s) MATCH-END',
                           lg_name, lvl, logging.getLevelName(lvl))

        return [TC()]


"""
The following classes are all derived from _OutputScannerBase. They each
set a different batch of command line args to nosetest, and define an
"expector" to tell the inherited methods in _OutputScannerBase what to do and look for.
"""


class OutputScannerBaseInfraRun(_OutputScannerBase):
    args = []
    _expector = _Expector('infra.run', 'DEBUG_5')


class LevelsForAnOutputInfraRun(_OutputScannerBase):
    args = ['--sm-set-logger-level', 'infra.run', 'DEBUG_7']
    _expector = _Expector('infra.run', 'DEBUG_7')


class LevelsForAnOutputInfraData(_OutputScannerBase):
    args = ['--sm-set-logger-level', 'infra.data', 'DEBUG_9']
    _expector = _Expector('infra.data', 'DEBUG_9')


class LevelsForAnOutputTestRun(_OutputScannerBase):
    args = ['--sm-set-logger-level', 'test.run', 'WARNING_5']
    _expector = _Expector('test.run', 'WARNING_5')


class LevelsForAnOutputTestData(_OutputScannerBase):
    args = ['--sm-set-logger-level', 'test.data', 'INFO_9']
    _expector = _Expector('test.data', 'INFO_9')


class HandlerRemapForALogger(_OutputScannerBase):
    """
    Note: this is paired with _OutputScannerBaseInfraRun, since that "proves" that
    by default, no debug is making it into log-capture. THIS lets the debugs out.
    """
    args = ['--sm-set-logger-level', 'infra.run', 'DEBUG_7',
            '--sm-set-handler-level', 'console-capture', 'DEBUG_5']
    _expector = _Expector('infra.run', 'DEBUG_7', concap_at='DEBUG_5')


class ComboRemapForALoggerSingleHandler(_OutputScannerBase):
    """
    This options sets the level of a given handler AND any logger feeding it.
    This will test a fairly basic footprint of that. Note that this argument
    is basically the equiv of the combo of logger and handler levels set in
    HandlerRemapForALogger.
    """
    args = ['--sm-set-combo-level', 'console-capture', 'DEBUG_6']
    _expector = _Expector('infra.run', 'DEBUG_6', concap_at='DEBUG_6')


class ComboRemapForALoggerGlobHandlers(_OutputScannerBase):
    """
    Same as ComboRemapForALoggerSingleHandler, but we grab both console and
    console-capture handlers via wildcard.
    """
    args = ['--sm-set-combo-level', 'console*', 'DEBUG_8']
    _expector = _Expector('infra.run', 'DEBUG_8', concap_at='DEBUG_8', real_at='DEBUG_8')


class SetFileLevelTestAtD7(_OutputScannerBase):
    args = ['--sm-set-file-level', 'test_logopts.py', '*', 'DEBUG_7']
    _expector = _Expector('infra.run', 'DEBUG_7', concap_at='DEBUG_7', real_at='DEBUG_7')
    # note: todo/missing test -> also inject into a 2nd logger and only see data from IT at info
