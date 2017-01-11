import plugin_test_helper
import os
import re
import sys

class _TempLogfileObserver(object):
    """
    We don't HAVE the stupid stream monitors yet, so this hack allows
    us to do basic content testing on the log files infra-logging generated.

    This class gets the logging dir from flogging, figures out where we "are" in
    the file at the moment, and is then able to do simple regex checking in the
    data from that point forward (kinda like an "tail -f x.log | fgrep <patterns>")
    """
    def __init__(self, lg_name):
        # defer import till here in order to avoid messing up infra-logging
        # during test loads
        from flogging import logger_get_logging_dir
        self.__full_name = os.path.join(logger_get_logging_dir(), lg_name)
        self.__current_length = os.stat(self.__full_name).st_size

    def __get_tail_chunk(self):
        log_data = ''
        with open(self.__full_name, 'r') as log_file:
            log_file.seek(self.__current_length)
            log_data = log_file.read()
        return log_data

    def check_for_line(self, test, line_re, exp_count):
        fdata = self.__get_tail_chunk()
        matches = 0
        re_matcher = re.compile(line_re)
        for line in fdata.split('\n'):
            if re_matcher.search(line):
                matches += 1

        test.assertTrue(
            matches == exp_count, 
            'Saw {0} rather than expected {1} of "{2}" in {3}, raw=[[[{4}]]]'.format(
                matches, exp_count, line_re, self.__full_name, fdata))
        

class _TempLogfileChecker(object):
    """
    Crude logfile checker that holds the "business logic" to check for backtraces and
    capture stdout or stderr contents (or lack thereof!)
    """
    def __init__(self, file_name):
        self.__lf_observer = _TempLogfileObserver(file_name)

    def __check_line(self, test, line_re, exp_count):
        self.__lf_observer.check_for_line(test, line_re, exp_count)
                
    def check_backtrace(self, test, ltype, suitepath, test_class, test_file, test_method, exp_count):
        full_file = os.path.join(suitepath, test_file)
        tb_line = '{0}\straceback: Traceback \(most recent call last\):'.format(ltype)
        self.__check_line(test, tb_line, exp_count)
        file_line = 'File "{0}", line \d+, in {1}'.format(full_file, test_method)
        self.__check_line(test, file_line, exp_count)

    def check_capture(self, test, cap_type, cap_level, test_class, test_method, exp_count):
        """
        param test: test-case (to do test.assertEqual on)
        param cap_type: 'stdout' or 'stderr'
        param cap_level: 'ERROR' or 'WARNING'
        param test_class: test class name
        param test_method: method name in test class
        param exp_count: expected sightings in file
        
        """
        eline = '{0}\s{1}:'.format(cap_level, cap_type)
        self.__check_line(test, eline, exp_count)
        # Need to check for expected match-data and NOT match data.
        self.__check_match_data(test, cap_type, test_class, test_method, exp_count)

    def __check_match_data(self, test, which_out, test_class, test_method, exp_count):
        md_prefix = '{0}-MATCH-DATA: {1}'.format(which_out.upper(), test_class)
        # Make sure setUp shows up in the one we want.
        # todo: stream-monitor when we get to it should be able to grab all stdout:
        #  for example.
        setup_re = '{0}: {1} setUp'.format(which_out, md_prefix)
        self.__check_line(test, setup_re, exp_count)
        method_re = '{0} {1}'.format(md_prefix, test_method)
        self.__check_line(test, method_re, exp_count)
        # should see NONE of these:
        no_see_re = '{0}-MUST-NOT-SEE:'.format(which_out.upper())
        self.__check_line(test, no_see_re, 0)
        

class TestSMPLoggingSingleOk(plugin_test_helper.resolve_helper_class()):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'one_pass')

    def verify(self):
        self._check_sequence_pre_test()
        self._check_sequence_test('test_single_log_to_run (test_one_log_pass.TestOneLoggerTest)')
        self._check_sequence_post_test()

class TestSMPLoggingTwoOk(plugin_test_helper.resolve_helper_class()):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'two_pass')
    _test_file = 'test_two_log_pass'
    _test_class = 'TestTwoLoggerTest'
    _test_methods = ['test_one_of_two_to_run','test_two_of_two_to_run']

    def verify(self):
        self._check_sequence_pre_test()
        self._check_sequences(self._test_methods, self._test_class, self._test_file)
        self._check_sequence_post_test()

class _BacktraceBase(plugin_test_helper.resolve_helper_class()):
    """
    Kind of a first stab at a more general plugin tester. I want to use
    the same suitepath based test file, but I want to have a test for each
    log file and so on. 

    subclasses need to define klass._backtrace_finder_file and
    klass._backtrace_finger_count. This base class will verify that the
    backtrace appears in that file the expected number of times
    """
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'backtrace')
    _test_file = 'test_backtrace'
    _test_class = 'TestLoggerBacktrace'
    _test_methods = ['test_backtrace_from_oops']
    _expect_nose_success = False

    def setUp(self):
        self.__logfile_checker = _TempLogfileChecker(self._backtrace_finder_file)
        super(_BacktraceBase, self).setUp()
        
    def verify(self):
        self.__logfile_checker.check_backtrace(
            self, 'ERROR', self.suitepath, self._test_class,
            self._test_file + '.py', self._test_methods[0],
            self._backtrace_finder_count)

        self._check_sequence_pre_test()
        self._check_sequences(self._test_methods, self._test_class, self._test_file)
        self._check_sequence_post_test()

class TestSMPLoggingBacktrace_all_all_error(_BacktraceBase):
    _backtrace_finder_file = 'all_all.log'
    _backtrace_finder_count = 2

class TestSMPLoggingBacktrace_infra_run_error(_BacktraceBase):
    _backtrace_finder_file = 'infra_run.log'
    _backtrace_finder_count = 1

class TestSMPLoggingBacktrace_test_run_error(_BacktraceBase):
    _backtrace_finder_file = 'test_run.log'
    _backtrace_finder_count = 1

class TestSMPLoggingBacktrace_infra_data_error(_BacktraceBase):
    _backtrace_finder_file = 'infra_data.log'
    _backtrace_finder_count = 0

class TestSMPLoggingBacktrace_test_data_error(_BacktraceBase):
    _backtrace_finder_file = 'test_data.log'
    _backtrace_finder_count = 0

class TestSMPLoggingBacktrace_console_capture_error(_BacktraceBase):
    _backtrace_finder_file = 'console_capture.log'
    _backtrace_finder_count = 1

class _CaptureBase(plugin_test_helper.resolve_helper_class()):
    _capture_method = None
    def setUp(self):
        self.__logfile_checker = _TempLogfileChecker(self._capture_finder_file)
        super(_CaptureBase, self).setUp()
        
    def verify(self):
        if self._capture_method is None:
            cm = self._test_methods[0]  # default to first
        else:
            cm = self._capture_method
        self.__logfile_checker.check_capture(
            self, self._capture_type, self._capture_level, self._test_class, cm, 
            self._capture_finder_count)

        self._check_sequence_pre_test()
        self._check_sequences(self._test_methods, self._test_class, self._test_file)
        self._check_sequence_post_test()

class _StdoutNoCaptureBase(_CaptureBase):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'stdout_nocap')
    _test_file = 'test_stdout_nocap'
    _test_class = 'TestLoggerStdoutNoError'
    _test_methods = ['test_stdout_from_testcase']
    _capture_type = 'stdout'
    _capture_level = 'ERROR'  # doesn't really matter, since counts are all zero.
    _capture_finder_count = 0
    _expect_nose_success = False

class TestSMPLoggingStdout_all_all_no_error(_StdoutNoCaptureBase):
    _capture_finder_file = 'all_all.log'
class TestSMPLoggingStdout_infra_run_no_error(_StdoutNoCaptureBase):
    _capture_finder_file = 'infra_run.log'
class TestSMPLoggingStdout_infra_data_no_error(_StdoutNoCaptureBase):
    _capture_finder_file = 'infra_data.log'
class TestSMPLoggingStdout_test_run_no_error(_StdoutNoCaptureBase):
    _capture_finder_file = 'test_run.log'
class TestSMPLoggingStdout_test_data_no_error(_StdoutNoCaptureBase):
    _capture_finder_file = 'test_data.log'
class TestSMPLoggingStdout_console_capture_no_error(_StdoutNoCaptureBase):
    _capture_finder_file = 'console_capture.log'


class _StdoutErrCaptureBase(_CaptureBase):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'stdout_errcap')
    _test_file = 'test_stdout_errcap'
    _test_class = 'TestLoggerStdoutError'
    _test_methods = ['test_no_stdout_from_testcase', 'test_stdout_from_testcase']
    _capture_type = 'stdout'
    _capture_level = 'ERROR'
    _capture_method = 'test_stdout_from_testcase'
    _expect_nose_success = False

class TestSMPLoggingStdout_all_all_error(_StdoutErrCaptureBase):
    _capture_finder_file = 'all_all.log'
    _capture_finder_count = 2
class TestSMPLoggingStdout_infra_run_error(_StdoutErrCaptureBase):
    _capture_finder_file = 'infra_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStdout_infra_data_error(_StdoutErrCaptureBase):
    _capture_finder_file = 'infra_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStdout_test_run_error(_StdoutErrCaptureBase):
    _capture_finder_file = 'test_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStdout_infra_data_error(_StdoutErrCaptureBase):
    _capture_finder_file = 'test_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStdout_console_capture_error(_StdoutErrCaptureBase):
    _capture_finder_file = 'console_capture.log'
    _capture_finder_count = 1

class _StdoutFailCaptureBase(_CaptureBase):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'stdout_failcap')
    _test_file = 'test_stdout_failcap'
    _test_class = 'TestLoggerStdoutFail'
    _test_methods = ['test_no_stdout_from_testcase', 'test_stdout_from_testcase']
    _capture_type = 'stdout'
    _capture_level = 'WARNING'
    _capture_method = 'test_stdout_from_testcase'
    _expect_nose_success = False

class TestSMPLoggingStdout_all_all_fail(_StdoutFailCaptureBase):
    _capture_finder_file = 'all_all.log'
    _capture_finder_count = 2
class TestSMPLoggingStdout_infra_run_fail(_StdoutFailCaptureBase):
    _capture_finder_file = 'infra_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStdout_infra_data_fail(_StdoutFailCaptureBase):
    _capture_finder_file = 'infra_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStdout_test_run_fail(_StdoutFailCaptureBase):
    _capture_finder_file = 'test_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStdout_infra_data_fail(_StdoutFailCaptureBase):
    _capture_finder_file = 'test_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStdout_console_capture_fail(_StdoutFailCaptureBase):
    _capture_finder_file = 'console_capture.log'
    _capture_finder_count = 1

class _StderrNoCaptureBase(_CaptureBase):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'stderr_nocap')
    _test_file = 'test_stderr_nocap'
    _test_class = 'TestLoggerStderrNoError'
    _test_methods = ['test_stderr_from_testcase']
    _capture_type = 'stderr'
    _capture_level = 'ERROR'  # doesn't really matter, since counts are all zero.
    _capture_finder_count = 0
    _expect_nose_success = False

class TestSMPLoggingStderr_all_all_no_error(_StderrNoCaptureBase):
    _capture_finder_file = 'all_all.log'
class TestSMPLoggingStderr_infra_run_no_error(_StderrNoCaptureBase):
    _capture_finder_file = 'infra_run.log'
class TestSMPLoggingStderr_infra_data_no_error(_StderrNoCaptureBase):
    _capture_finder_file = 'infra_data.log'
class TestSMPLoggingStderr_test_run_no_error(_StderrNoCaptureBase):
    _capture_finder_file = 'test_run.log'
class TestSMPLoggingStderr_test_data_no_error(_StderrNoCaptureBase):
    _capture_finder_file = 'test_data.log'
class TestSMPLoggingStderr_console_capture_no_error(_StderrNoCaptureBase):
    _capture_finder_file = 'console_capture.log'


class _StderrErrCaptureBase(_CaptureBase):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'stderr_errcap')
    _test_file = 'test_stderr_errcap'
    _test_class = 'TestLoggerStderrError'
    _test_methods = ['test_no_stderr_from_testcase', 'test_stderr_from_testcase']
    _capture_type = 'stderr'
    _capture_level = 'ERROR'
    _capture_method = 'test_stderr_from_testcase'
    _expect_nose_success = False

class TestSMPLoggingStderr_all_all_error(_StderrErrCaptureBase):
    _capture_finder_file = 'all_all.log'
    _capture_finder_count = 2
class TestSMPLoggingStderr_infra_run_error(_StderrErrCaptureBase):
    _capture_finder_file = 'infra_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStderr_infra_data_error(_StderrErrCaptureBase):
    _capture_finder_file = 'infra_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStderr_test_run_error(_StderrErrCaptureBase):
    _capture_finder_file = 'test_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStderr_infra_data_error(_StderrErrCaptureBase):
    _capture_finder_file = 'test_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStderr_console_capture_error(_StderrErrCaptureBase):
    _capture_finder_file = 'console_capture.log'
    _capture_finder_count = 1

class _StderrFailCaptureBase(_CaptureBase):
    suitepath = plugin_test_helper.resolve_suitepath('stream-source', 'logging', 'stderr_failcap')
    _test_file = 'test_stderr_failcap'
    _test_class = 'TestLoggerStderrFail'
    _test_methods = ['test_no_stderr_from_testcase', 'test_stderr_from_testcase']
    _capture_type = 'stderr'
    _capture_level = 'WARNING'
    _capture_method = 'test_stderr_from_testcase'
    _expect_nose_success = False

class TestSMPLoggingStderr_all_all_fail(_StderrFailCaptureBase):
    _capture_finder_file = 'all_all.log'
    _capture_finder_count = 2
class TestSMPLoggingStderr_infra_run_fail(_StderrFailCaptureBase):
    _capture_finder_file = 'infra_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStderr_infra_data_fail(_StderrFailCaptureBase):
    _capture_finder_file = 'infra_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStderr_test_run_fail(_StderrFailCaptureBase):
    _capture_finder_file = 'test_run.log'
    _capture_finder_count = 1
class TestSMPLoggingStderr_infra_data_fail(_StderrFailCaptureBase):
    _capture_finder_file = 'test_data.log'
    _capture_finder_count = 0
class TestSMPLoggingStderr_console_capture_fail(_StderrFailCaptureBase):
    _capture_finder_file = 'console_capture.log'
    _capture_finder_count = 1

