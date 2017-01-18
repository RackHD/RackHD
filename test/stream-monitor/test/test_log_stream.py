import plugin_test_helper
import os
import re
import sys
from log_stream_helper import TempLogfileChecker


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
        self.__logfile_checker = TempLogfileChecker(self._backtrace_finder_file)
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
        self.__logfile_checker = TempLogfileChecker(self._capture_finder_file)
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

