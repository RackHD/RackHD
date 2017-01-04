from logging import Logger, DEBUG, INFO, getLoggerClass
from logging import getLogger as real_getLogger
from logging import _srcfile  # yes, this is evil. No, we don't have a choice.
from .monitor_abc import StreamMonitorABC
import sys

class LoggingMarker(StreamMonitorABC):
    _all_blocks = 0
    def __init__(self):
        # import HERE to prevent taking over logfiles for things
        # like 'nosetests --help'.
        import flogging
        self.__print_to = None
        # Uncomment next line to view steps to console live
        # self.__print_to = sys.stderr
        # todo: use nose plugin debug options
        self.__loggers = self.__find_loggers()
        self.__test_cnt = 0

    @classmethod
    def enabled_for_nose(self):
        return True

    def handle_begin(self):
        self.__loggers = self.__find_loggers()
        self.__mark_all_loggers(str(self._all_blocks), 'start-of-all-tests')
        self._all_blocks += 1

    def handle_start_test(self, test):
        ts = '+{0}'.format(self.__test_cnt)
        self.__mark_all_loggers(ts, '-------STARTING TEST: %s--------', str(test))

    def handle_stop_test(self, test):
        ts = '-{0}'.format(self.__test_cnt)
        self.__test_cnt += 1
        self.__mark_all_loggers(ts, '--------ENDING TEST: %s--------', str(test))

    def __mark_all_in_logger(self, level, logger, msg, args, exc_info=None, extra=None):
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

    def __mark_logger_block(self, logger, bracket, level, fmat, *args, **kwargs):
        # rep_cnt is used to fill in about X (20) chars with the repeated
        # text.
        rep_cnt = int(20/len(bracket))
        self.__mark_all_in_logger(level, logger, bracket * rep_cnt, [])
        self.__mark_all_in_logger(level, logger, fmat, args, **kwargs)
        self.__mark_all_in_logger(level, logger, bracket * rep_cnt, [])

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

