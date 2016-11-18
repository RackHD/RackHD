"""
Copyright 2017, EMC, Inc.

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


class _GeventInfoAdapter(logging.LoggerAdapter):
    _main_greenlet = gevent.getcurrent()
    # todo: trim 'pathname' to root of tree, not global
    #  and log shortening event (to keep abs context)
    #  breadcrumb: filters rather than adapters
    # todo: add logger name to output
    def process(self, msg, kwargs):
        cur = gevent.getcurrent()
        if cur == self._main_greenlet:
            gname = 'main'
        else:
            gname = getattr(cur, 'log_facility', str(cur))
        msg = '(greenlet:{0!s}) {1!s}'.format(gname, msg)
        return msg, kwargs

    def __getattr__(self, key):
        """
        We didn't have the attribute, so try our logger...
        """
        sub_func = getattr(self.logger, key)
        if sub_func is None:
            m = "'{0}' object has no attribute '{1}'".format(self.__name__, key)
            raise AttributeError(m)
        return sub_func


class _LevelLoggerClass(Logger):
    _log_call_matcher = re.compile(r'''^(?P<base>[a-zA-Z]\w*?)_(?P<post_num>\d)$''')
    def __getattr__(self, key):
        """
        We intercept getattrs and map look for entries of the form:
          levelname_0 to levelname_9 and map them to a call to self._log at that
        the base level for levelname plus or minus the value of the _n part
        of the attribute. An example is easier to understand:
        A Logger instance has a .debug() method, which uses the int value
        of DEBUG to check/emit. DEBUG happens to be equal to the int 10.
        debug_0 ends up mapping to the int value 5 (DEBUG - 5).
        debug_5 ends up mapping to the int value 10 (DEBUG - 0)
        debug_9 ends up mapping to the int value 14 (DEBUG + 5)

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
        actual_value = _levelNames[base_name] + val_adj - 5

        def wrapper(msg, *args, **kw):
            return self._log(actual_value, msg, args, kw)

        # We return a wrapper function, since we are being asked to resolve
        # the method, not call it. The above wrapper allows us to return
        # something callable that still allows us to inject the calculated
        # level-value.
        return wrapper


class _LoggerSetup(object):
    def __init__(self):
        self.__prelog_data = []
        self.__do_dirs()
        self.__do_level_names()
        self.__do_config()
        lg = getInfraRunLogger()
        for level, fmat, args, kwargs in self.__prelog_data:
            lg.log(level, fmat, *args, **kwargs)

    def __prelog(self, level, fmat, *args, **kwargs):
        self.__prelog_data.append( (level, fmat, args, kwargs) )

    def __makedirs_dash_p(self, *args, **kwargs):
        try:
            os.makedirs(*args, **kwargs)
        except OSError, e:
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
                             -                                # '-'
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
        trim_these = keys[3:]
        for trim_inx in trim_these:
            trim_name = os.path.join(lg_base_dir, matches[trim_inx])
            self.__prelog(logging.INFO, 'removing previous logging dir %s', trim_name)
            shutil.rmtree(trim_name)

        ts_ext = datetime.now().strftime('%Y-%m-%d_%X')
        self.__lg_run_dir = os.path.join(lg_base_dir, 'run_{0}.d'.format(ts_ext))
        self.__prelog(logging.INFO, "this runs logging dir %s", self.__lg_run_dir)
        self.__makedirs_dash_p(os.path.join(self.__lg_run_dir))

        # now deal with and easy to use 'last'
        last_name = os.path.join(lg_base_dir, 'run_last.d')
        if os.path.islink(last_name):
            os.unlink(last_name)

        assert not os.path.lexists(last_name), \
            "'{0}' still existed after unlink. Check for file/dir and remove manually".format(last_name)
        os.symlink(self.__lg_run_dir, last_name)

        self.__infra_run_lgn = os.path.join(self.__lg_run_dir, 'infra_run.log')
        self.__infra_data_lgn = os.path.join(self.__lg_run_dir, 'infra_data.log')
        self.__test_run_lgn = os.path.join(self.__lg_run_dir, 'test_run.log')
        self.__test_data_lgn = os.path.join(self.__lg_run_dir, 'test_data.log')
        self.__console_capture_lgn = os.path.join(self.__lg_run_dir,
                                                  'console_capture.log')

    def __do_level_names(self):
        lvl_copy = dict(_levelNames)
        for adj in xrange(0,10):
            for lvl_key, lvl_value in lvl_copy.items():
                if isinstance(lvl_key, str) and lvl_key != 'NOTSET':
                    new_name = "{0}_{1}".format(lvl_key, 9 - adj)
                    new_val = lvl_value + (9 - adj) - 5
                    if new_val != lvl_value:
                        addLevelName(new_val, new_name)

    def __do_config(self):
        # todo: NOT have this stuff show up in nosetests w/o -v or something
        # base config dict. Must conform to
        # https://docs.python.org/2/library/logging.config.html#logging-config-dictschema
        cdict = {
            'version': 1,
            'handlers': {
                'console': {
                    # catch all. May not need to exist?
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'simple'
                },
                'console-capture': {
                    'level': 'INFO',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__console_capture_lgn,
                    'formatter': 'simple'
                },
                'infra-run': {
                    # the test infrastructure code (not the tests themselves)
                    # I.E., like logging about logging :)
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__infra_run_lgn,
                    'formatter': 'simple'
                },
                'infra-data': {
                    # test infra data. for example, storing of expect stuff
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__infra_data_lgn,
                    'formatter': 'simple'
                },
                'test-run': {
                    # test-run code. I.E., where tests can say "I'm doing X"
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__test_run_lgn,
                    'formatter': 'simple'
                },
                'test-data': {
                    # raw data from actual tests. Like the infra-data
                    'level': 'DEBUG',
                    'class': 'logging.handlers.RotatingFileHandler',
                    'filename': self.__test_data_lgn,
                    'formatter': 'simple'
                },
            },
            'loggers': {
                '': {
                    'handlers': ['console', 'console-capture'],
                    'propagate': True,
                    'level': 'INFO',
                    'stream': 'ext://sys.stdout'
                },
                'infra.run': {
                    'handlers': ['infra-run'],
                    'propagate': True,
                    'level': 'DEBUG',
                },
                'infra.data': {
                    'handlers': ['infra-data'],
                    'propagate': True,
                    'level': 'DEBUG',
                },
                'test.run': {
                    'handlers': ['test-run'],
                    'propagate': True,
                    'level': 'DEBUG',
                },
                'test.data': {
                    'handlers': ['test-data'],
                    'propagate': True,
                    'level': 'DEBUG',
                }
            },
            'formatters': {
                'simple': {
                    'format': '%(asctime)s %(process)d %(processName)s '
                              '%(pathname)s:%(funcName)s@%(lineno)d %(levelname)s %(message)s'
                }
            }
        }
        logging.config.dictConfig(cdict)


setLoggerClass(_LevelLoggerClass)

def getLogger(name=None):
    if name is None:
        rl = logging.getLogger()
    else:
        rl = logging.getLogger(name)
    rl = _GeventInfoAdapter(rl, {})
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

if __name__ == '__main__':
    print logging.root.handlers
    lg = logging.getLogger('foo')
    lg.info_9('hello')
    lg.info('xxx')
