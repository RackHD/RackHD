"""
Copyright 2017, EMC, Inc.
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


class TempLogfileChecker(object):
    """
    Crude logfile checker that holds the "business logic" to check for backtraces and
    capture stdout or stderr contents (or lack thereof!)
    """
    def __init__(self, file_name, stringio_override = None):
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
        line_re = r'''^\d\d\d\d-\d\d-\d\d\s     # '2017-01-12 '
                      \d\d:\d\d:\d\d,\d\d\d\s   # '10:10:46,106 '
                      (?P<level>\S+)\s+         # 'WARNING_9 ' or 'INFO   '
                      MATCH-START\s             # 'MATCH-START '
                      (?P<logger_name>\S+)\s    # 'infra.run '
                      (?P<levelno>\d+)\(        # '28('
                      (?P<level_name>\S+?)\)\s  # 'WARNING_2) '
                      MATCH-END\s+              # 'MATCH-END    '
                      .*?$                      # rest-of-line
                      '''
        if start_at_levelno is None:
            test_levelno = 1  # lowest legal value
            info_base = 'not-matches-expected, lg_name={0}'.format(lg_name)
            exp_count = 0
        else:
            test_levelno = start_at_levelno
            info_base = 'start_at_levelno={0}, lg_name={1}'.format(start_at_levelno, lg_name)
            # "CRITICAL" is our max log-value injected in makeSuite in test_logopts.pyh
            exp_count = logging.getLevelName('CRITICAL') - test_levelno

        count = 0
        for match in self.__lf_observer.iter_on_re(line_re):
            count += 1
            test_level_name = levelno_to_name(test_levelno)
            pass_info = '({0}, test_level_name={1}, test_levelno={2})'.format(
                info_base, test_level_name, test_levelno)
            found_log_level_name = match.group("level")
            found_msg_logger_name = match.group("logger_name")
            found_msg_levelno = int(match.group("levelno"))
            found_msg_level_name = match.group("level_name")
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


def levelno_to_name(levelno):
    """
    This test infra does not have access to the plugins expanded
    logger names. So, find the base number and then add an _<remaimder>
    for non-predefined levels.
    """
    # this will turn 21 into 20, 20 into 20, 15 into 10 and so on.
    adjusted_tens =    (4 + levelno) / 10
    adjusted_base =    (adjusted_tens * 10)
    name = logging.getLevelName(adjusted_base)
    remainder = (4 + levelno) % 10
    # and reverse because remainder is currently reversed vs range.
    remainder = 9 - remainder
    if remainder != 5:
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
        ret_val = base_value + (5 - offset_val)
    else:
        ret_val = logging.getLevelName(level_name)
    return ret_val
