"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import os
import re
import logging


class _TempLogfileObserver(object):
    """
    We don't HAVE the stupid stream monitors yet, so this hack allows
    us to do basic content testing on the log files infra-logging generated.

    This class gets the logging dir from flogging, figures out where we "are" in
    the file at the moment, and is then able to do simple regex checking in the
    data from that point forward (kinda like an "tail -f x.log | fgrep <patterns>")

    Cludgely handles both real files and stringio ones.
    """
    def __init__(self, lg_name, stringio_override=None):
        if stringio_override is None:
            # defer import till here in order to avoid messing up infra-logging
            # during test loads
            from flogging.infra_logging import logger_get_logging_dir
            self.__full_name = os.path.join(logger_get_logging_dir(), lg_name)
            self.__current_length = os.stat(self.__full_name).st_size
        else:
            self.__full_name = lg_name
            self.__current_length = stringio_override.len
        self.__stringio_override = stringio_override

    def __get_tail_chunk(self):
        log_data = ''
        if self.__stringio_override is None:
            with open(self.__full_name, 'r') as log_file:
                log_file.seek(self.__current_length)
                log_data = log_file.read()
        else:
            log_file = self.__stringio_override
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

    def iter_on_re(self, iter_re):
        fdata = self.__get_tail_chunk()
        return re.finditer(iter_re, fdata, re.VERBOSE | re.MULTILINE)

    def iter_on_line(self):
        fdata = self.__get_tail_chunk()
        for line in fdata.split('\n'):
            # Note: we need to skip internal logging message. It might be better
            # to hunt for the corect ones, but since there are other tests to
            # cover formatting etc of each type, trying to track new internal logs
            # doesn't gain us much and costs a lot.
            if 'stream-monitor/stream_sources/' in line:
                continue

            yield line


class TempLogfileChecker(object):
    """
    Crude logfile checker that holds the "business logic" to check for backtraces and
    capture stdout or stderr contents (or lack thereof!)
    """
    _upto_msg_re = r'''^\d\d\d\d-\d\d-\d\d\s           # '2017-01-12 '
                       \d\d:\d\d:\d\d,\d\d\d\s         # '10:10:46,106 '
                       (?P<level_name>\S+)\s+          # 'INFO '
                       '''

    def __init__(self, file_name, stringio_override=None):
        self.__lf_observer = _TempLogfileObserver(file_name, stringio_override)
        self.__file_name = file_name

    def __check_line(self, test, line_re, exp_count):
        self.__lf_observer.check_for_line(test, line_re, exp_count)

    def check_backtrace(self, test, ltype, suitepath, test_class, test_file, test_method, exp_count):
        full_file = os.path.join(suitepath, test_file)
        tb_line = '{0}\s+traceback: Traceback \(most recent call last\):'.format(ltype)
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
        eline = '{0}\s+{1}:'.format(cap_level, cap_type)
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

    def check_level_output(self, test, start_at_levelno, lg_name):
        """
        Routine to look into our file for the last test duration and see if we saw (or didn't see)
        the right log records. We are looking for (in a normal logger output line)
        * The right progression of string levels IN the message part of the line
        * The right progression of string levels in the level part of the line. (same as prior ^^^)
        * The right level number that matches the string level.
        * The expected logger name in the message part of the line.

        The "progression" means starting at the start_at_levelno value and going to CRITICAL (the
        max level the logging system will in theory produce. kind of). Or, if the start_at_levelno
        is None, we expect to NOT see anything!
        """
        line_re = self._upto_msg_re + '''             # 'timestamp INFO   '
                      MATCH-START\s                   # 'MATCH-START '
                      (?P<logger_name>\S+)\s          # 'infra.run '
                      (?P<levelno>\d+)\(              # '28('
                      (?P<match_level_name>\S+?)\)\s  # 'WARNING_2) '
                      MATCH-END\s+                    # 'MATCH-END    '
                      .*?$                            # rest-of-line
                      '''
        if start_at_levelno is None:
            test_levelno = 1  # lowest legal value
            exp_count = 0
        else:
            test_levelno = start_at_levelno
            # "CRITICAL_0" is our max log-value injected in makeSuite in test_logopts.pyh
            #  That -seems- backwards at first glance, but this is the -threshold- value we are
            #  working with normally. In this case, CRITICAL_0 will hold the highest possible int
            #  value that CAN be checked against.
            exp_count = logging.getLevelName('CRITICAL_0') - test_levelno

        count = 0
        for match in self.__lf_observer.iter_on_re(line_re):
            count += 1
            test_level_name = levelno_to_name(test_levelno)
            found_log_level_name = match.group("level_name")
            found_msg_logger_name = match.group("logger_name")
            found_msg_levelno = int(match.group("levelno"))
            found_msg_level_name = match.group("match_level_name")
            test.assertEqual(test_levelno, found_msg_levelno,
                             'expected levelno {0} != found levelno {1}'.format(
                                 test_levelno, found_msg_levelno))
            test.assertEqual(test_level_name, found_msg_level_name,
                             'expected msg levelname {0} != found {1}'.format(
                                 test_level_name, found_msg_level_name))
            test.assertEqual(test_level_name, found_log_level_name,
                             'expected logger levelname {0} != found {1}'.format(
                                 test_level_name, found_log_level_name))
            test.assertEqual(lg_name, found_msg_logger_name,
                             'expected logger name {0} != found {1}'.format(
                                 lg_name, found_msg_logger_name))
            test_levelno += 1
        test.assertEqual(count, exp_count,
                         'Expected {0} matches, but only saw {1}'.format(exp_count, count))

    def __check_sobs(self, test, line_iter, lg_names):
        """
        Utility method for check_full_format to take a closer look at the lines like:
        "2017-02-22 10:31:11,348 DEBUG    Start Of Test Block: 3                                                infra.data"

        The method checks:
        * if a line appears for each expected lg_names
        * all lines that match have the same test-block value

        It also returns the test-block-number
        """
        sob_re = self._upto_msg_re + r'''                       # time-stamp + 'INFO '
                            Start\sOf\sTest\sBlock:\s+         # 'Start Of Test Block: '
                            (?P<block_number>\d+)\s+           # '1       '
                            (?P<line_logger_name>\S+)\s*$      # 'infra.run'<eol>
                            '''
        in_consume = True
        cre = re.compile(sob_re, re.VERBOSE)
        found = 0
        tcn = None
        exp_lines = len(lg_names)
        found_lg_names = []
        for inx in range(0, exp_lines):
            line = line_iter.next()
            if in_consume:
                if 'removing previous logging dir' in line:
                    continue
                if 'this runs logging dir' in line:
                    continue
                in_consume = False
            m = cre.match(line)
            test.assertIsNotNone(
                m, "'{0}' did not match '{1}' {2} of {3}".format(line, sob_re, found, exp_lines))
            found += 1
            if tcn is None:
                tcn = m.group('block_number')
            test.assertEqual(tcn, m.group('block_number'),
                             'already found block {0} and now found {1}'.format(
                             tcn, m.group('block_number')))
            found_lg_names.append(m.group('line_logger_name'))
        test.assertSetEqual(set(lg_names), set(found_lg_names),
                            "logger names from normal line format do not match expected")
        return tcn

    def __check_start_tests(self, test, line_iter, lg_names, test_block, test_name):
        """
        Utility method for check_full_format to take a closer look at the lines like:
        "2017-02-22 10:31:11,349 DEBUG   +3.01 - STARTING TEST: [runTest (test_log_stream_fmat.TC)]                  infra.data"

        The method checks:
        * if a line appears for each expected lg_names
        * if the test-block number matches the one passed in as test_block
        * if test_name is same as passed in as test_name

        It also returns the full test-case-number we will expect in further lines in this batch.
        """
        st_re = self._upto_msg_re + r'''                  # time-stamp + 'INFO '
                       \+(?P<tc_number>\S+)\s             # '+1.01 '
                       -\sSTARTING\sTEST:\s+              # '- STARTING TEST: '
                       \[(?P<test_name>.*?)\]\s+          # '[testTest (test_moo.TC)]  '
                       (?P<line_logger_name>.*?)\s+$      # 'infra.run'<eol>
                       '''
        cre = re.compile(st_re, re.VERBOSE)
        found = 0
        tcn = None
        found_lg_names = []
        for lg_name in lg_names:
            line = line_iter.next()
            m = cre.match(line)
            test.assertIsNotNone(
                m, "'{0}' did not match '{1}' {2} of {3}".format(line, st_re, found, len(lg_names)))
            found += 1
            found_tcn = m.group('tc_number')
            if tcn is None:
                found_block, found_tn = found_tcn.split('.', 1)
                test.assertEqual(found_block, test_block,
                                 'found test-block {0} in {1}, but expected was {2}'.format(
                                     found_block, found_tcn, test_block))
                tcn = found_tcn
            test.assertEqual(found_tcn, tcn,
                             'found test-number {0} but expected was {1}'.format(
                                 found_tcn, tcn))
            found_lg_names.append(m.group('line_logger_name'))
            found_test_name = m.group('test_name')
            test.assertEqual(
                found_test_name, test_name,
                "found test name '{0}' but was expected '{1}'".format(
                    found_test_name, test_name))
        test.assertSetEqual(set(lg_names), set(found_lg_names),
                            "logger names from normal line format do not match expected")
        return tcn

    def __check_main_lines(self, test, line_iter, lg_names, tcn, test_name, call_file):
        """
        Utility method for check_full_format to take a close look at the lines like:
        2017-02-22 10:02:54,207 INFO    MATCH-FMAT-START root MATCH-FMAT-END                                                       root >1.01 77927 MainProcess stream-monitor/test/test_log_stream_fmat.py:runTest@19 gl-main [runTest (test_log_stream_fmat.TC)]"  # noqa E501

        Validates:
        * logger names found both inside the message AND in the logger-name slot match list of loggers from lg_names
        * test-case-number from line matches passed in tcn
        * pid matches os.getpid()
        * process-name is 'MainProcess' (needs own test for multiproc)
        * call_file argument ends with the call_file value from line (call_file param is entire path)
        * method-name from line matches "testRun" (all that can show up in plugin tests)
        * line-no from line is a positive int
        * greenlet field from line is 'gl-main' (needs own test for other greenlets)
        * test-name field from line matches passed in test-name
        """
        main_line_re = self._upto_msg_re + r'''           # time-stamp + 'INFO  '
                       MATCH-FMAT-START\s+                # 'MATCH-FMAT-START  '
                       (?P<match_logger_name>\S+)\s+      # 'infra.run '
                       MATCH-FMAT-END\s+                  # 'MATCH-FMAT-END  '
                       (?P<line_logger_name>\S+)\s+       # 'infra.run '
                       >(?P<tc_number>\S+)\s              # '>1.01 '
                       (?P<pid>\d+)\s                     # '1234   '
                       (?P<process_name>\S+)\s            # 'MainProcess '
                       (?P<call_file>\S+):                # 'stream-monitor/test/foo.py:'
                       (?P<method_name>\S+)@              # 'runTest@'
                       (?P<line_no>\d+)\s+                # '19 '
                       (?P<greenlet>\S+)\s+               # 'gl-main '
                       \[(?P<test_name>.*?)\]$            # '[testTest (test_moo.TC)]eol'
                       '''
        cre = re.compile(main_line_re, re.VERBOSE)
        found = 0
        found_match_lg_names = []
        found_line_lg_names = []
        for lg_name in lg_names:
            line = line_iter.next()
            m = cre.match(line)
            test.assertIsNotNone(
                m, "did not match '{0}' {1} of {2} [[{3}]]".format(
                    main_line_re, found, len(lg_names), line))
            found += 1
            found_tcn = m.group('tc_number')
            test.assertEqual(found_tcn, tcn,
                             'found test-number {0} but expected was {1} [[{2}]]'.format(
                                 found_tcn, tcn, line))
            found_line_lg_names.append(m.group('line_logger_name'))
            found_match_lg_names.append(m.group("match_logger_name"))
            found_test_name = m.group('test_name')
            test.assertEqual(
                found_test_name, test_name,
                "found test name '{0}' but was expected '{1}'".format(
                    found_test_name, test_name))
            found_greenlet = m.group('greenlet')
            exp_greenlet = 'gl-main'    # no test for this yet, so hard code
            test.assertEqual(found_greenlet, exp_greenlet, 'found greenlet {0} expected {1}'.format(
                found_greenlet, exp_greenlet))
            found_pid = m.group('pid')
            exp_pid = str(os.getpid())
            test.assertEqual(found_pid, exp_pid, "found pid '{0}' expected '{1}'".format(
                found_pid, exp_pid))
            pname = m.group('process_name')
            epname = 'MainProcess'    # no test for this yet, so hard unicode
            test.assertEqual(pname, epname, 'found process-name {0} expected {1}'.format(
                pname, epname))
            found_call_file = m.group('call_file')
            test.assertTrue(call_file.endswith(found_call_file),
                            "found call-file '{0}' that did not match end-of expected file {1}".format(
                                found_call_file, call_file))
            mname = m.group('method_name')
            emname = 'runTest'         # currently fixed. Add as arg if expanding
            test.assertEqual(mname, emname, 'found method-name {0} expected {1}'.format(
                mname, emname))
            line_no = m.group('line_no')
            # nothing we can really do with this in terms of matching. Make sure
            # it is an int just to test something.
            int(line_no)
            test.assertTrue(line_no > 0, 'line number {0} not a positive number'.format(
                line_no))
        test.assertSetEqual(set(lg_names), set(found_line_lg_names),
                            "logger names from normal line format do not match expected")
        test.assertSetEqual(set(lg_names), set(found_match_lg_names),
                            "logger names from message section do not match expected")

    def __check_end_tests(self, test, line_iter, lg_names, tcn, test_name):
        """
        Utility method for check_full_format to take a close look at the lines like:
        "2017-02-22 10:02:54,475 INFO    -5.01 - ENDING TEST: [runTest (test_log_stream_fmat.TC)]                        root"

        The method checks:
        * if a line appears for eache expected lg_names
        * if the test-case number matches passed in one as tcn
        * if test_name is same as passed in as test_name
        """
        et_re = self._upto_msg_re + r'''                  # time-stamp + 'INFO '
                       -(?P<tc_number>\S+)\s+             # '-1.01 '
                       -\sENDING\sTEST:\s+                # '- ENDING TEST: '
                       \[(?P<test_name>.*?)\]\s+          # '[testTest (test_moo.TC)]  '
                       (?P<line_logger_name>.*?)\s*$      # 'infra.run'<eol>
                       '''
        cre = re.compile(et_re, re.VERBOSE)
        found = 0
        found_lg_names = []
        for lg_name in lg_names:
            line = line_iter.next()
            m = cre.match(line)
            test.assertIsNotNone(
                m, "did not match '{0}' {1} of {2}".format(et_re, found, len(lg_names)))
            found += 1
            found_tcn = m.group('tc_number')
            test.assertEqual(found_tcn, tcn,
                             'found test-number {0} but expected was {1}'.format(
                                 found_tcn, tcn))
            found_lg_names.append(m.group('line_logger_name'))
            found_test_name = m.group('test_name')
            test.assertEqual(
                found_test_name, test_name,
                "found test name '{0}' but was expected '{1}'".format(
                    found_test_name, test_name))
        test.assertSetEqual(set(lg_names), set(found_lg_names),
                            "logger names from normal line format do not match expected")

    def check_full_format(self, test, match_lg_names, bracketing_lg_names, test_name, calling_file):
        """
        Checker method for test_log_stream_fmat.py's tests.

        It coordinates:
        * getting a line iterator from the log-file observer
        * checking for Start Of Test Block sanity, which also yields the current test-block-number
        * checking for "STARTING TEST:" sanity, which also yields the current test-case-number
          (block-#:test-in-block-#)
        * checking for the injected MATCH-FMAT-... lines
        * checking for "ENDING TEST:" sanity

        param test: unitest.TestCase instance to call asserts from
        param match_lg_names: list of logger names that must appear in the main-lines section
        param bracketing_lg_names: list of logger names that must appear in the start-of-block, start-tests,
            end-tests sections.
        param test_name: string name to match test-name from lines against.
        param calling_file: value of test files __file__.
        """
        data_iter = self.__lf_observer.iter_on_line()
        test_block = self.__check_sobs(test, data_iter, bracketing_lg_names)
        tcn = self.__check_start_tests(test, data_iter, bracketing_lg_names, test_block, test_name)
        self.__check_main_lines(test, data_iter, match_lg_names, tcn, test_name, calling_file)
        self.__check_end_tests(test, data_iter, bracketing_lg_names, tcn, test_name)


def levelno_to_name(levelno):
    """
    This test infra does not have access to the plugins expanded
    logger names. So, find the base number and then add an _<remaimder>
    for non-predefined levels.

    Each base name (DEBUG, INFO, etc) covers a range from base + 2 for base_0 to base - 7 for base_9.
    Or more accuratlly: base + (2 - X) (where 'X' is the number from base_#.
    For example debug_0 is 12 and debug_9 is 3.
    So first we want to isolate the tens digit for the range we are in to get the base...
    """
    # Add 7 to the levelno to shift into right ten's place (3->10 and 12->19)
    adjusted_tens = (7 + levelno) / 10
    adjusted_base = (adjusted_tens * 10)
    name = logging.getLevelName(adjusted_base)
    # Now get the part to hang out after the '_'.
    remainder = (7 + levelno) % 10
    # and reverse because remainder is currently reversed vs range.
    remainder = 9 - remainder
    if remainder != 2:
        name = '{0}_{1}'.format(name, remainder)
    return name


def levelname_to_number(level_name):
    """
    This test infra does not have access to the plugins expanded
    logger names. This function will take a name and figure out the raw
    number value.
    """
    if '_' in level_name:
        base_name, num_str = level_name.split('_', 1)
        base_value = logging.getLevelName(base_name)
        offset_val = int(num_str)
        ret_val = base_value + (2 - offset_val)
    else:
        ret_val = logging.getLevelName(level_name)
    return ret_val
