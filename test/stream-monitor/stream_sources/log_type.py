from logging import Logger, DEBUG, INFO, getLoggerClass
from logging import getLogger as real_getLogger
from logging import _srcfile  # yes, this is evil. No, we don't have a choice.
from .monitor_abc import StreamMonitorABC
import sys
from itertools import count


class _StreamToLogger(object):
    def __init__(self, logger):
        """
        This is a fake stream-ish device to allow us to turn raw
        stream data into logger calls to the passed in logger.

        Buffers output to new-line boundaries (to allow catching:
        "running test foo ... ok" as one entry.
        """
        self.__use_logger = logger
        self.__buffer = ''

    def write(self, data):
        self.__buffer += data
        while '\n' in self.__buffer:
            line, rest = self.__buffer.split('\n', 1)
            self.__use_logger.info('%s', line)
            self.__buffer = rest

    def flush(self):
        pass

    def real_flush(self):
        if len(self.__buffer) > 0:
            self.__use_logger('%s', line)
            self.__buffer = ''


class LoggingMarker(StreamMonitorABC):
    _all_blocks = 0

    def __init__(self):
        # import HERE to prevent taking over logfiles for things
        # like 'nosetests --help'. Note that a generic "import flogging" won't trigger this.
        # We need to explicity pull the infra_logging module.
        import flogging.infra_logging
        self.__config_reset_method = flogging.infra_logging.logger_reset_configuration
        self.__print_to = None
        # Uncomment next line to view steps to console live
        # self.__print_to = sys.stderr
        # todo: use nose plugin debug options
        self.__loggers = self.__find_loggers()
        self.__test_cnt = 1
        self.__nose_status_logger = _StreamToLogger(flogging.get_loggers().irl)

    @classmethod
    def enabled_for_nose(self):
        return True

    def reset_configuration(self):
        """
        Basically for use during plugin self-test, which runs multiple complete
        test life-cycles for the plugins, but this watcher needs to survive
        between them. The config of levels, etc, however, does NOT!

        Note: __config_reset_method is pulled from the flogging module in __init__.
        """
        self.__config_reset_method()

    def get_nose_stream_logger(self):
        return self.__nose_status_logger

    def handle_begin(self):
        self.__loggers = self.__find_loggers()
        self._all_blocks += 1
        self.__test_cnt = 1
        self.__mark_all_loggers('', ' Start Of Test Block: {}'.format(self._all_blocks))

    def handle_start_test(self, test):
        self.__mark_all_loggers('', 
                                '+{0}.{1:02d} - STARTING TEST: %s'.format(self._all_blocks, self.__test_cnt), 
                                str(test))

    def handle_stop_test(self, test):
        self.__mark_all_loggers('', 
                                '-{0}.{1:02d} - ENDING TEST: %s'.format(self._all_blocks, self.__test_cnt), 
                                str(test))
        self.__test_cnt += 1

    def __mark_all_in_logger(self, level, logger, msg, args, exc_info=None, extra=None):
        # Note: 'handlers' only exists on Logger() instances.
        handlers = getattr(logger, 'handlers', [])
        if len(handlers) == 0:
            return  # Nothing to do!
        if _srcfile:
            #IronPython doesn't track Python frames, so findCaller raises an
            #exception on some versions of IronPython. We trap it here so that
            #IronPython can use logging.
            try:
                fn, lno, func = logger.findCaller()
            except ValueError:
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        else:
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info:
            if not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        record = logger.makeRecord(logger.name, level, fn, lno, msg, args, exc_info, func, extra)
        for handler in handlers:
            handler.handle(record)

    def __capture_to_log(self, lg, log_level, cap_type, test, sout, serr, tb):
        """
        Common routine to push capture data into a logger at a given level.
        Note: this, along with "handle_capture" are a bit of a stop-gap for
        RAC-3869. Well, technically this is a solution for this one case, but
        RAC-3869 covers the general logcapture case, and this would make use
        of its abilities rather than manually walking loggers in handle_capture
        and dealing with propagate in such a hacky fashion here.
        """
        save_propagate = lg.propagate
        try:
            lg.propagate = 0
            lg.log(log_level, '------start captured data for %s in %s', cap_type, test)
            lg.log(log_level, 'stdout: %s', sout)
            lg.log(log_level, 'stderr: %s', serr)
            lg.log(log_level, 'traceback: %s', tb)
            lg.log(log_level, '------end captured data for %s in %s', cap_type, test)
        except:
            lg.propagate = save_propagate
            raise
        lg.propagate = save_propagate

    def handle_capture(self, log_level, cap_type, test, sout, serr, traceback):
        """
        StreamMonitorPlugin call-if-present method to handle moving
        post-test capture data (in the case of error or failures) into
        the logs. We decide which loggers to add to (currently hard coded
        to the infra.run, test.run, and the root), and then use __capture_to_log to
        do the common work.
        """
        irlg = real_getLogger('infra.run')
        self.__capture_to_log(irlg, log_level, cap_type, test, sout, serr,
                              traceback)
        trlg = real_getLogger('test.run')
        self.__capture_to_log(trlg, log_level, cap_type, test, sout, serr,
                              traceback)
        root = real_getLogger()
        self.__capture_to_log(root, log_level, cap_type, test, sout, serr,
                              traceback)

    def __mark_logger_block(self, logger, bracket, level, fmat, *args, **kwargs):
        if bracket:
            # rep_cnt is used to fill in about X (20) chars with the repeated
            # text.
            rep_cnt = int(20/len(bracket))
            self.__mark_all_in_logger(level, logger, bracket * rep_cnt, [])
            self.__mark_all_in_logger(level, logger, fmat, args, **kwargs)
            self.__mark_all_in_logger(level, logger, bracket * rep_cnt, [])
        else:
            self.__mark_all_in_logger(level, logger, fmat, args, **kwargs)

    def __mark_all_loggers(self, bracket, fmat, *args, **kwargs):
        root = real_getLogger()
        self.__mark_logger_block(root, bracket, INFO, fmat, *args, **kwargs)
        for logger in self.__loggers.values():
            self.__mark_logger_block(logger, bracket, DEBUG, fmat, *args, **kwargs)

    def __find_loggers(self):
        ldict = Logger.manager.loggerDict
        # todo: feature -> add test-name to all log handlers if we can.
        observed_loggers = {}
        observed_handlers = {}
        # For now, only do our loggers. TODO: we need to be capturing ALL the
        # loggers (not just ours), but we don't want 'mark alls' hitting the
        # console because of them.
        for lg_name, logger in ldict.items():
            if lg_name not in ['infra.run', 'infra.data', 'test.run', 'test.data', '']:
                if self.__print_to is not None:
                    print >>self.__print_to, "SKIPPING {0}  -> {1}".format(lg_name, logger)
            else:
                if self.__print_to is not None:
                    print >>self.__print_to, "OBSERVING {0}  -> {1}".format(lg_name, logger)
                handlers = getattr(logger, 'handlers', None)
                if handlers is None:
                    if self.__print_to is not None:
                        print >>self.__print_to, "   no handlers on {0} type {1}".format(logger, type(logger))
                else:
                    for handler in handlers:
                        if self.__print_to is not None:
                            print >>self.__print_to, "   handler = {0} {1}".format(handler, handler.get_name())
                        observed_handlers[handler] = handler
                observed_loggers[lg_name] = logger

        return observed_loggers

