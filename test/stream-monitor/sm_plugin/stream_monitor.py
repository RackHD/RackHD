"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import logging
import os
from nose.plugins import Plugin
from stream_sources import LoggingMarker, SelfTestStreamMonitor, AMQPStreamMonitor, SSHHelper
import sys
from nose.pyversion import format_exception
from nose.plugins.xunit import Tee
from nose import SkipTest
from StringIO import StringIO
from logging import ERROR, WARNING
from flogging import LoggerArgParseHelper, get_loggers


class StreamMonitorPlugin(Plugin):
    _singleton = None
    name = "stream-monitor"
    encoding = 'UTF-8'

    def __init__(self, *args, **kwargs):
        assert StreamMonitorPlugin._singleton is None, \
            "infrastructure fault: more than one StreamMonitorPlugin exists"
        StreamMonitorPlugin._singleton = self
        self.__save_call_sequence = None
        self.__print_to = None
        # Uncomment next line to view steps to console live
        # self.__print_to = sys.stderr
        # todo: use nose plugin debug options.
        self.__stream_plugins = {}
        self.__capture_stack = []
        self.__current_stdout = None
        self.__current_stderr = None
        super(StreamMonitorPlugin, self).__init__(*args, **kwargs)

    @classmethod
    def get_singleton_instance(klass):
        assert klass._singleton is not None, \
            "Attempt to retrieve singleton before first instance created"
        return klass._singleton

    def _self_test_print_step_enable(self):
        self.__save_call_sequence = []

    def _self_test_sequence_seen(self):
        rl = self.__save_call_sequence
        self.__save_call_sequence = []
        return rl

    def __take_step(self, name, **kwargs):
        if self.__save_call_sequence is not None:
            self.__save_call_sequence.append((name, kwargs))

        if self.__print_to is not None:
            print >>self.__print_to, 'ESTEP: {0} {1}'.format(name, kwargs)

    def options(self, parser, env=os.environ):
        self.__take_step('options', parser=parser, env=env)
        self.__log = logging.getLogger('nose.plugins.streammonitor')
        self.__flogger_opts_helper = LoggerArgParseHelper(parser)
        AMQPStreamMonitor.add_nose_parser_opts(parser)
        SSHHelper.add_nose_parser_opts(parser)
        super(StreamMonitorPlugin, self).options(parser, env=env)

    def configure(self, options, conf):
        self.__take_step('configure', options=options, conf=conf)
        super(StreamMonitorPlugin, self).configure(options, conf)
        if not self.enabled:
            return
        if getattr(conf.options, 'collect_only', False):
            # we don't want to be spitting stuff out during -list!
            self.enabled = False

    def finalize(self, result):
        self.__take_step('finalize', result=result)
        self.__call_all_plugin_by_attr('handle_finalize')
        self.__log.info('Stream Monitor Report Complete')

    def __call_all_plugin_by_attr(self, attr_name, *args, **kwargs):
        for pg in self.__stream_plugins.values():
            method = getattr(pg, attr_name, None)
            if method is not None:
                method(*args, **kwargs)

    def begin(self):
        self.__take_step('begin')
        # tood: check class "enabled_for_nose()"
        SSHHelper.set_options(self.conf.options)
        if len(self.__stream_plugins) == 0:
            self.__stream_plugins['logging'] = LoggingMarker()
            self.__stream_plugins['self-test'] = SelfTestStreamMonitor()
            self.__stream_plugins['amqp'] = AMQPStreamMonitor()
        else:
            # This is basically for self-testing the plugin, since the
            # logging monitor stays around between test-classes. If we don't do
            # this, the prior logging settings "stick".
            self.__stream_plugins['logging'].reset_configuration()

        self.__flogger_opts_helper.process_parsed(self.conf.options)
        self.__stream_plugins['amqp'].set_options(self.conf.options)

        self.__call_all_plugin_by_attr('handle_set_flogging', get_loggers())
        self.__call_all_plugin_by_attr('handle_begin')

    def beforeTest(self, test):
        # order is beforeTest->startTest->stopTest->afterTest
        self.__take_step('beforeTest', test=test)
        self.__start_capture()
        self.__call_all_plugin_by_attr('handle_before_test', test)

    def afterTest(self, test):
        self.__take_step('afterTest', test=test)
        self.__call_all_plugin_by_attr('handle_after_test', test)
        self.__end_capture()
        self.__current_stdout = None
        self.__current_stderr = None

    def startTest(self, test):
        self.__take_step('startTest', test=test)
        self.__call_all_plugin_by_attr('handle_start_test', test)

    def stopTest(self, test):
        self.__take_step('stopTest', test=test)
        self.__call_all_plugin_by_attr('handle_stop_test', test)

    def __start_capture(self):
        """
        __start_capture and __end_capture bracket a zone of time that we might want to
        dump captured information from. E.G. we normally don't WANT to see stdout and stderr
        from "test_did_this_work()"... unless they fail. In which case, we want to see them!

        Both capture and logcapture report all this at the END of the entire run, however.
        This is great and very handy (since they are all there at the end of the run). But,
        in the context of looking at a single test, it's really annoying. So, this logic
        is stolen from the xunit plugin (which does capture better than capture!). We are
        basically tucking away stdout/stderrs while letting the data flow to prior levels
        using the Tee.
        """
        self.__capture_stack.append((sys.stdout, sys.stderr))
        self.__current_stdout = StringIO()
        self.__current_stderr = StringIO()
        sys.stdout = Tee(self.encoding, self.__current_stdout, sys.stdout)
        sys.stderr = Tee(self.encoding, self.__current_stderr, sys.stderr)

    def __end_capture(self):
        if self.__capture_stack:
            sys.stdout, sys.stderr = self.__capture_stack.pop()

    def __get_captured_stdout(self):
        if self.__current_stdout:
            value = self.__current_stdout.getvalue()
            if value:
                return value
        return ''

    def __get_captured_stderr(self):
        if self.__current_stderr:
            value = self.__current_stderr.getvalue()
            if value:
                return value
        return ''

    def startContext(self, context):
        self.__start_capture()

    def stopContext(self, context):
        self.__end_capture()

    def addError(self, test, err):
        """
        Handle capturing data on an error being seen. If the "error"
        is a Skip, we don't care at this point. Otherwise,
        we want to grab our stdout, stderr, and traceback and asking
        logging to record all this stuff about the error.

        Note: since 'errors' are related to _running_ the test (vs the
        test deciding to fail because of an incorrect value), we asking
        logging to record it as an error.
        """
        if issubclass(err[0], SkipTest):
            # Nothing to see here...
            return

        self.__propagate_capture(ERROR, 'ERROR', test, err)

    def addFailure(self, test, err):
        """
        Handle capturing data on a failure being seen. This covers the case
        of a test deciding it failed, so we record as a warning level.
        """
        self.__propagate_capture(WARNING, 'FAIL', test, err)

    def __propagate_capture(self, log_level, cap_type, test, err):
        """
        Common routine to recover capture data and asking logging to
        deal with it nicely.
        """
        tb = format_exception(err, self.encoding)
        sout = self.__get_captured_stdout()
        serr = self.__get_captured_stderr()
        self.__call_all_plugin_by_attr('handle_capture', log_level, cap_type, test, sout, serr, tb)

    def get_stream_monitor_by_name(self, name):
        return self.__stream_plugins[name]


def smp_get_stream_monitor_plugin():
    """
    Get the plugin that nose will have created. ONLY nose should
    create the main instance!
    """
    smp = StreamMonitorPlugin.get_singleton_instance()
    return smp


def smp_get_stream_monitor(monitor_name):
    smp = StreamMonitorPlugin.get_singleton_instance()
    return smp.get_stream_monitor_by_name(monitor_name)
