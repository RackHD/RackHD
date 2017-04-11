"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
from __future__ import print_function
import unittest
import os
import sys
from nose.plugins import PluginTester
from sm_plugin import StreamMonitorPlugin
from log_stream_helper import TempLogfileChecker
from StringIO import StringIO


class _BaseStreamMonitorPluginTester(PluginTester, unittest.TestCase):
    activate = '--with-stream-monitor'
    _smp = StreamMonitorPlugin()
    _smp._self_test_print_step_enable()
    _purge_step_sequence = True
    longMessage = True
    plugins = [_smp]

    def tearDown(self):
        """
        Check the _purse_step_sequence and clear out the self-test-sequence
        record if set. This base-class doesn't do verification of the results, nor
        does it check the sequence. _BaseStreamMonitorPluginTesterVerify does both,
        and will thus set the purge-var to valse.
        """
        if self._purge_step_sequence:
            self._smp._self_test_sequence_seen()


class _BaseStreamMonitorPluginTesterVerify(_BaseStreamMonitorPluginTester):
    _expect_nose_success = True
    _purge_step_sequence = False

    def runTest(self):
        # This is called once for each class derived from it. We don't really
        # have access to much other than success/failure and the raw string output
        # for -all- the tests that were run in the derived class.

        # We print out the output from the run tests, trusting in the capture
        # code to hide it.
        print('*' * 70)
        for what in self.output:
            print("> {0}".format(what.rstrip()))
        print('*' * 70)

        # Now check for success (_expect_nose_success can be set by a subclass
        # to mark that it expects an error to occur, and then let it handle its
        # own checking inside its verify)
        if self._expect_nose_success:
            self.assertTrue(self.nose.success,
                            '----a contained test or tests failed----')

        self.__call_sequence = self._smp._self_test_sequence_seen()
        self.verify()
        assert len(self.__call_sequence) == 0, \
            'still had call-items left at end {0}'.format(self.__call_sequence)

    def verify(self):
        raise NotImplementedError()

    def _check_sequence_pre_test(self):
        self.__check_next('options', ['parser', 'env'])
        self.__check_next('configure', ['options', 'conf'])
        self.__check_next('begin', [])

    def _check_sequences(self, methods, test_class, test_file):
        for method in methods:
            test_name = '{0} ({1}.{2})'.format(method, test_file, test_class)
            self._check_sequence_test(test_name)

    def _check_sequence_test(self, test_name):
        self.__check_next('beforeTest', ['test'], {'test': test_name})
        self.__check_next('startTest', ['test'], {'test': test_name})
        self.__check_next('stopTest', ['test'], {'test': test_name})
        self.__check_next('afterTest', ['test'], {'test': test_name})

    def _check_sequence_post_test(self):
        # disable flake8 for log_dict not being used. The act of
        # getting it makes sure it got filled in.
        log_dict = self.__check_next('finalize', ['result'])  # noqa: F841
        # todo: poke into log_dict for run/errors/failures.
        # (it's like {'result': <nose.result.TextTestResult run=1 errors=0 failures=0>})

    def __check_next(self, step_name, required_keys, match_dict=None):
        if len(self.__call_sequence) == 0:
            next_thing = ('no-more-steps-found', {})
        else:
            next_thing = self.__call_sequence[0]
            self.__call_sequence = self.__call_sequence[1:]

        next_name, next_args = next_thing
        assert step_name == next_name, \
            "Was expecting step '{0}', but got '{1}'.".format(step_name, next_name)
        rset = set(required_keys)
        naset = set(next_args.keys())
        req_not_there = rset - naset
        assert len(req_not_there) == 0, \
            "Required key(s) missing: {0} from {1} on step {2}".format(
                req_not_there, naset, step_name)
        there_not_req = naset - rset
        assert len(there_not_req) == 0, \
            "Extra key(s): {0} beyond {1} on step {2}".format(
                there_not_req, rset, step_name)

        if match_dict is not None:
            for arg_key, arg_str in match_dict.items():
                assert arg_key in next_args, \
                    "Argument {0} was supposed to have value {1} but was missing".format(
                        arg_key, arg_str)
                m_str = str(next_args[arg_key])
                assert arg_str == m_str, \
                    "Argument {0} was supposed to have value '{1}' but was '{2}'".format(
                        arg_key, arg_str, m_str)


class _BaseLogOutScannerBase(_BaseStreamMonitorPluginTester):
    """
    Plugin tester instance used for each real test block.
    """
    def setUp(self, *args, **kwargs):
        """
        This is called before all the test in the block, but in the context of the
        plugin-under-test. We do the following:
        * replace stderr with a StringIO stream.
        * start a dict of log-file to our cheesy log-file-checkers on the stderr streamio.
        * add to the dict of log-files with a cheesy log-file-checkers for each physical log file.
        * init our super (to finish any wiring IT has to do)
        """
        checker_dict = {}
        self.__save_stderr = sys.stderr
        self.__stream_stderr = StringIO()
        sys.stderr = self.__stream_stderr
        checker_dict['stderr'] = TempLogfileChecker('stderr', self.__stream_stderr)

        lg_names = ['all_all.log', 'console_capture.log', 'infra_data.log',
                    'infra_run.log', 'test_data.log', 'test_run.log']
        for lg_name in lg_names:
            checker_dict[lg_name] = TempLogfileChecker(lg_name)
        self._lgfile_watchers = checker_dict
        super(_BaseLogOutScannerBase, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        """
        The mirror of setUp. We restore stderr and then do our one magic trick:
        We clear out the call sequence of the stream-monitor plugin. WE don't use it, but
        can't turn it off and if we don't clear it, OUR calls will end up in the
        next test's sequence!
        """
        sys.stderr = self.__save_stderr
        self._smp._self_test_sequence_seen()
        super(_BaseLogOutScannerBase, self).tearDown(*args, **kwargs)


def resolve_helper_class():
    return _BaseStreamMonitorPluginTesterVerify


def resolve_no_verify_helper_class():
    return _BaseStreamMonitorPluginTester


def resolve_logoutput_scanner_helper_class():
    return _BaseLogOutScannerBase


def resolve_suitepath(*args):
    support = os.path.join(os.path.dirname(__file__), 'support')
    return os.path.join(support, *args)
