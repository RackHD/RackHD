"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This file contains the mechanisms to do logging from within
the test infrastructure.

todo: this is the 1st shot. More stories are stacked up to add readmes, examples, et al.
"""
from logging import Logger, setLoggerClass, _levelNames, addLevelName
from datetime import datetime
import logging
import logging.config
import logging.handlers
import re
import gevent
import os
import errno
import shutil


class _GeventInfoFilter(logging.Filter):
    _main_greenlet = gevent.getcurrent()

    def __init__(self, *args, **kwargs):
        super(_GeventInfoFilter, self).__init__(*args, **kwargs)

        # determine the root of the tree we are running from. Quick and
        # ugly right now (might be nice to 'hunt' upwards for root files etc,
        # but since this particular file is not likely to move around, this
        # may be all we need.
        our_dir = os.path.dirname(os.path.abspath(__file__))
        # pop up two levels to the 'fit_tests' directory.
        test_dir = os.path.dirname(os.path.dirname(our_dir))
        self.__path_trim = test_dir + '/'
        self.__current_test_name = 'any tests'
        self.__current_test_case_number = '**.**'

    def sm_set_running_test(self, test_case_number, test_name):
        """
        Method to allow a stream-monitor plugin for test execution to tell us where
        in execution we are.
        param test_case_number: string of a test-case number for this test. Also includes
            '+' for setup, '-' for teardown, '=' for in, and '*' for after.
        param test_name: actual test name (may contain spaces)
        """
        self.__current_test_name = test_name
        self.__current_test_case_number = test_case_number

    # todo: trim 'pathname' to root of tree, not global
    #  and log shortening event (to keep abs context)
    # todo: add logger name to output
    def filter(self, record):
        if record.pathname.startswith(self.__path_trim):
            record.pathname = record.pathname[len(self.__path_trim):]
        cur = gevent.getcurrent()
        if cur == self._main_greenlet:
            gname = 'gl-main'
        else:
            gname = getattr(cur, 'log_facility', str(cur))
        record.greenlet = '{0!s}'.format(gname)
        record.test_name = self.__current_test_name
        record.test_case_number = self.__current_test_case_number

        # This section removes the process, path, and greenlet information
        # from any mssage that starts with any of the characters ' +-'.
        # These are well known stream monitor messages and this informtion
        # is not required to be displayed.
        # TODO: there is probably a better way to do this but this will
        #       work until it is setup.
        if any(elem in record.msg[0] for elem in r' +-?%'):
            lif = ''
        else:
            u_lif = '{r.test_case_number} {r.process} {r.processName} {r.pathname}:{r.funcName}@{r.lineno} ' + \
                '{r.greenlet} [{r.test_name}]'
            lif = u_lif.format(r=record)
        record.location_info_string = lif

        return True

    def __str__(self):
        return 'infra-context-adding-filter'


class _LevelLoggerClass(Logger):
    _log_call_matcher = re.compile(r'''^(?P<base>[a-zA-Z]\w*?)_(?P<post_num>\d)$''')

    def __getattr__(self, key):
        """
        We intercept getattrs and map look for entries of the form:
          levelname_0 to levelname_9 and map them to a call to self._log at that
        the base level for levelname plus or minus the value of the _n part
        of the attribute. An example is easier to understand:
        A Logger instance has a .debug() method, which uses the int value
        of DEBUG to check/emit. DEBUG happens to be equal to the int 10. The following
        list shows the name and numeric value of each debug_n (or DEBUG_n)
        name           int-value    'on'-by-default     note
        debug_0        12           yes
        debug_1        11           yes
        debug_2        10           yes                 DEBUG synonym
        debug_3         9           yes
        debug_4         8           yes
        debug_5         7           yes                 most detailed 'always on'
        debug_6         6            no
        debug_7         5            no
        debug_8         4            no
        debug_9         3            no

        Since the logging system treats higher int values as "more important"
        (e.g. CRITICAL is 50), this means debug_9 would be used to represent
        finer-grained (more detailed) information than straight DEBUG.

        This code matches anything for the form alpha-chars_n, which ends
        up handling the following methods:
        critical, fatal, error, warning, warn, info, debug, exception

        Note that those base methods are resolved directly, and this method
        is not called for those.
        """
        attr_match = self._log_call_matcher.match(key)
        if attr_match is None:
            m = "'{0}' object has no attribute '{1}'".format(self.__name__, key)
            raise AttributeError(m)

        base_name = attr_match.group("base").upper()
        val_adj = int(attr_match.group("post_num"))
        actual_value = _levelNames[base_name] + (2 - val_adj)

        def wrapper(msg, *args, **kw):
            return self.log(actual_value, msg, *args, **kw)

        # We return a wrapper function, since we are being asked to resolve
        # the method, not call it. The above wrapper allows us to return
        # something callable that still allows us to inject the calculated
        # level-value.
        return wrapper


class _LoggerSetup(object):
    _SAVED_LOGDIR_COUNT = 10

    def __init__(self):
        self.__prelog_data = []
        self.__do_dirs()
        self.__do_level_names()
        self.__do_config()
        lg = getInfraRunLogger()
        for level, fmat, args, kwargs in self.__prelog_data:
            lg.log(level, fmat, *args, **kwargs)

    def __prelog(self, level, fmat, *args, **kwargs):
        self.__prelog_data.append((level, fmat, args, kwargs))

    def __makedirs_dash_p(self, *args, **kwargs):
        try:
            os.makedirs(*args, **kwargs)
        except OSError as e:
            # be happy if someone already created the path
            if e.errno != errno.EEXIST:
                raise

    def __do_dirs(self):
        our_dir = os.path.dirname(os.path.abspath(__file__))
        test_dir = os.path.dirname(os.path.dirname(our_dir))
        lg_base_dir = os.path.join(test_dir, 'log_output')
        self.__makedirs_dash_p(lg_base_dir)
        dirs_in_log = os.listdir(lg_base_dir)
        matcher = re.compile(r'''^                            # SOL
                             run_                             # 'run_'
                             (?P<run_date>\d\d\d\d-\d\d-\d\d  # 2016-11-18
                             _                                # '_'
                             \d\d:\d\d:\d\d)                  # 23:11:00
                             \.d$''',                         # '.d' EOL
                             re.VERBOSE)
        matches = {}
        for file_name in dirs_in_log:
            m = matcher.match(file_name)
            if m is not None:
                key = m.group("run_date")
                matches[key] = file_name

        keys = sorted(matches.keys(), reverse=True)
        trim_these = keys[self._SAVED_LOGDIR_COUNT:]
        for trim_inx in trim_these:
            trim_name = os.path.join(lg_base_dir, matches[trim_inx])
            self.__prelog(logging.INFO, 'removing previous logging dir %s', trim_name)
            shutil.rmtree(trim_name)

        ts_ext = datetime.now().strftime('%Y-%m-%d_%X')
        run_name = 'run_{0}.d'.format(ts_ext)
        self.__lg_run_dir = os.path.join(lg_base_dir, run_name)
        self.__prelog(logging.INFO, "this runs logging dir %s", self.__lg_run_dir)
        self.__makedirs_dash_p(os.path.join(self.__lg_run_dir))

        # now deal with and easy to use 'last'
        last_name = 'run_last.d'
        last_path = os.path.join(lg_base_dir, last_name)
        if os.path.islink(last_path):
            os.unlink(last_path)

        assert not os.path.lexists(last_path), \
            "'{0}' still existed after unlink. Check for file/dir and remove manually".format(last_name)
        cur_dir = os.getcwd()
        os.chdir(lg_base_dir)
        os.symlink(run_name, last_name)
        os.chdir(cur_dir)

        self.__infra_run_lgn = os.path.join(self.__lg_run_dir, 'infra_run.log')
        self.__infra_data_lgn = os.path.join(self.__lg_run_dir, 'infra_data.log')
        self.__test_run_lgn = os.path.join(self.__lg_run_dir, 'test_run.log')
        self.__test_data_lgn = os.path.join(self.__lg_run_dir, 'test_data.log')
        # all_all -> both _infra and _test AND both _run and _data.
        self.__combined_all_all_lgn = os.path.join(self.__lg_run_dir, 'all_all.log')
        self.__console_capture_lgn = os.path.join(self.__lg_run_dir,
                                                  'console_capture.log')

    def __do_level_names(self):
        lvl_copy = dict(_levelNames)
        for adj in range(0, 10):
            for lvl_key, lvl_value in lvl_copy.items():
                if isinstance(lvl_key, str) and lvl_key != 'NOTSET':
                    new_name = "{0}_{1}".format(lvl_key, adj)
                    new_val = lvl_value + (2 - adj)
                    # Note: we can't insert our overlap (DEBUG_2 == DEBUG)
                    # here without changing what _appears_ in the log to be the _2
                    # version. We let __getattr__ mapping handle this case.
                    if new_val != lvl_value:
                        addLevelName(new_val, new_name)

    def __do_config(self):
        # todo: NOT have this stuff show up in nosetests w/o -v or something
        # base config dict. Must conform to
        # https://docs.python.org/2/library/logging.config.html#logging-config-dictschema
        cdict = {
            'version': 1,
            'filters': {
                'ctx_add_filter': {
                    '()': _GeventInfoFilter
                }
            },
            'handlers': {
                'console': {
                    # catch all. May not need to exist?
                    'level': 'INFO_5',
                    'class': 'logging.StreamHandler',
                    'filters': ['ctx_add_filter'],
                    'formatter': 'simple'
                },
                'console-capture': {
                    'level': 'INFO_5',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__console_capture_lgn,
                    'filters': ['ctx_add_filter'],
                    'formatter': 'simple'
                },
                'infra-run': {
                    # the test infrastructure code (not the tests themselves)
                    # I.E., like logging about logging :)
                    'level': 'NOTSET',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__infra_run_lgn,
                    'filters': ['ctx_add_filter'],
                    'formatter': 'simple'
                },
                'infra-data': {
                    # test infra data. for example, storing of expect stuff
                    'level': 'NOTSET',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__infra_data_lgn,
                    'filters': ['ctx_add_filter'],
                    'formatter': 'simple'
                },
                'test-run': {
                    # test-run code. I.E., where tests can say "I'm doing X"
                    'level': 'NOTSET',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__test_run_lgn,
                    'filters': ['ctx_add_filter'],
                    'formatter': 'simple'
                },
                'test-data': {
                    # raw data from actual tests. Like the infra-data
                    'level': 'NOTSET',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__test_data_lgn,
                    'filters': ['ctx_add_filter'],
                    'formatter': 'simple'
                },
                'combined-all-all': {
                    # put the works into a single file
                    'level': 'NOTSET',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__combined_all_all_lgn,
                    'filters': ['ctx_add_filter'],
                    'formatter': 'simple'
                },
            },
            'loggers': {
                '': {
                    'handlers': ['console', 'console-capture'],
                    'propagate': True,
                    'level': 'INFO_5',
                    'stream': 'ext://sys.stdout'
                },
                'infra.run': {
                    'handlers': ['infra-run', 'combined-all-all'],
                    'propagate': True,
                    'level': 'DEBUG_5',
                },
                'infra.data': {
                    'handlers': ['infra-data', 'combined-all-all'],
                    'propagate': True,
                    'level': 'DEBUG_5',
                },
                'test.run': {
                    'handlers': ['test-run', 'combined-all-all'],
                    'propagate': True,
                    'level': 'DEBUG_5',
                },
                'test.data': {
                    'handlers': ['test-data', 'combined-all-all'],
                    'propagate': True,
                    'level': 'DEBUG_5',
                }
            },
            'formatters': {
                'simple': {
                    'format': '%(asctime)s %(levelname)-7s %(message)-90s'
                              ' %(name)s %(location_info_string)s'
                },
                'original': {
                    'format': '%(asctime)s %(process)d %(processName)s '
                              '%(pathname)s:%(funcName)s@%(lineno)d %(greenlet)s %(levelname)s %(message)s'
                }
            }
        }
        logging.config.dictConfig(cdict)
        # And squelch the annoying root level urllib messages!
        # (you do need both, alas).
        # todo: record this traffic in its own logfile?
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

    def reset_configuration(self):
        """
        Basically for use during plugin self-test, which runs multiple complete
        test life-cycles for the plugins, but this watcher needs to survive
        between them. The config of levels, etc, however, does NOT!
        """
        self.__do_config()

    def set_level(self, new_level):
        pass

    def get_logging_dir(self):
        """
        Right now mostly for test-test, but may enter infra-use later
        """
        return self.__lg_run_dir


setLoggerClass(_LevelLoggerClass)


def getLogger(name=None):
    if name is None:
        rl = logging.getLogger()
    else:
        rl = logging.getLogger(name)
    return rl


def _getLoggerBase(names, name):
    if name is not None:
        names.append(name)
    return getLogger('.'.join(names))


def getInfraRunLogger(name=None):
    return _getLoggerBase(['infra', 'run'], name)


def getInfraDataLogger(name=None):
    return _getLoggerBase(['infra', 'data'], name)


def getTestRunLogger(name=None):
    return _getLoggerBase(['test', 'run'], name)


def getTestDataLogger(name=None):
    return _getLoggerBase(['test', 'data'], name)


_logger_setup_instance = _LoggerSetup()


def logger_reset_configuration():
    _logger_setup_instance.reset_configuration()


def logger_config_api(verbosity):
    _logger_setup_instance.set_level(verbosity)


def logger_get_logging_dir():
    return _logger_setup_instance.get_logging_dir()
