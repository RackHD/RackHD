"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import plugin_test_helper
import unittest


class FullLineFormatChecker(plugin_test_helper.resolve_logoutput_scanner_helper_class()):
    def makeSuite(self):
        """
        Used for all out-test-cases to inject a log entry into each logger.
        """
        class TC(unittest.TestCase):
            def runTest(self):
                import logging
                lg_list = ['root', 'infra.run', 'infra.data', 'test.run', 'test.data']
                for lg_name in lg_list:
                    lg = logging.getLogger(lg_name)
                    lg.info('MATCH-FMAT-START %s MATCH-FMAT-END', lg_name)

        return [TC()]

    def __common_checker(self, logger_name):
        logger_file = logger_name.replace('.', '_') + '.log'
        self.__common_multi_logger_checker([logger_name], logger_file)

    def __common_multi_logger_checker(self, match_lg_names, logger_file, bracketing_lg_names=None):
        """
        Helper method to invoke the file-watcher for the requested logger_file.

        param match_lg_names is a list of logger names (like ['infra.run', 'infra.data']).
            These will be expected to appear in the actual lines injected by makeSuite.TC
        param logger_file is the key to our base-classes collection of file-watchers.
        param bracketing_lg_names is a list of logger names that will appear in various
            bracketing log lines (like "Start Of Test Block", "STARTING TEST", and "ENDING TEST")
            If left as None, it is populated with the match_lg_params.
        """
        if bracketing_lg_names is None:
            bracketing_lg_names = match_lg_names

        file_watcher = self._lgfile_watchers[logger_file]
        # alas, the test name is always our TC from makeSuite. Hard-code name:
        test_name = 'runTest (test_log_stream_fmat.TC)'
        our_file = __file__
        if our_file.endswith('.pyc'):
            our_file = our_file[:-1]  # turn into '.py' from '.pyc'!
        file_watcher.check_full_format(self, match_lg_names, bracketing_lg_names, test_name, our_file)

    def test_infra_run_file(self):
        self.__common_checker('infra.run')

    def test_infra_data_file(self):
        self.__common_checker('infra.data')

    def test_test_run_file(self):
        self.__common_checker('test.run')

    def test_test_data_file(self):
        self.__common_checker('test.data')

    def test_all_all(self):
        self.__common_multi_logger_checker(
            ['infra.data', 'test.data', 'test.run', 'infra.run'], 'all_all.log')

    def test_console_capture(self):
        self.__common_multi_logger_checker(
            ['infra.data', 'test.data', 'test.run', 'infra.run'], 'console_capture.log', ['root'])

    def test_stderr_capture(self):
        self.__common_multi_logger_checker(
            ['infra.data', 'test.data', 'test.run', 'infra.run'], 'stderr', ['root'])
