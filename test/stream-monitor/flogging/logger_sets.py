"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""


class _LoggerSet(object):
    def __init__(self, name=None):
        from .infra_logging import getInfraRunLogger, getInfraDataLogger, getTestRunLogger, getTestDataLogger
        self.irl = getInfraRunLogger(name=name)
        self.idl = getInfraDataLogger(name=name)
        self.trl = getTestRunLogger(name=name)
        self.tdl = getTestDataLogger(name=name)
        self.data_log = self.tdl

    def __getattr__(self, key):
        """
        Complete hack mode to present a logging.Logger style
        api with test-run-logger being the target. E.G.
        x = _LoggerSet()
        x.debug(...) is equiv to x.trl.debug(...)
        """
        if hasattr(self.trl, key):
            return getattr(self.trl, key)

        m = "'{0}' object has no attribute '{1}'".format(self.__class__, key)
        raise AttributeError(m)


def get_loggers(name=None):
    # todo: auto-push test-file name into the name of the logger
    return _LoggerSet(name=name)
