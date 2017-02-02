import unittest, os
import sys
from nose.plugins import PluginTester
from sm_plugin import StreamMonitorPlugin


class _BaseStreamMonitorPluginTester(PluginTester, unittest.TestCase):
    activate = '--with-stream-monitor'
    _smp = StreamMonitorPlugin()
    _smp._self_test_print_step_enable()
    _expect_nose_success = True
    plugins = [_smp]
    def runTest(self):
        # This is called once for each class derived from it. We don't really
        # have access to much other than success/failure and the raw string output
        # for -all- the tests that were run in the derived class.

        # We print out the output from the run tests, trusting in the capture
        # code to hide it. 
        print '*' * 70
        for what in self.output:
            print ">", what.rstrip()
        print '*' * 70

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
        log_dict = self.__check_next('finalize', ['result'])
        # todo: poke into log_dict for run/errors/failures.
        # (it's like {'result': <nose.result.TextTestResult run=1 errors=0 failures=0>})

    def __check_next(self, step_name, required_keys, match_dict=None):
        if len(self.__call_sequence) == 0:
            next_thing = ( 'no-more-steps-found', {} )
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


def resolve_helper_class():
    return _BaseStreamMonitorPluginTester

def resolve_suitepath(*args):
    support = os.path.join(os.path.dirname(__file__), 'support')
    return os.path.join(support, *args)
