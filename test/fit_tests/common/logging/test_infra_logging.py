"""
Copyright 2017, EMC, Inc.

This file contains (very very crude, at the moment!) self
tests of the logging infrastructure.
"""
import sys
from StringIO import StringIO
from proboscis import test
from infra_logging import *
from ..test_based_monitors import TestBasedMonitorTestCase


@test(groups=["test-infra-tester"])
class TestInfraLogging(TestBasedMonitorTestCase):
    """suite of tests to do basic sanity checking of infra-logging abilities"""

    def setUp(self):
        # Not every test needs to stare into
        # stdout, but we want to make sure
        # we always restore it if we do.
        self.__save_stdout = sys.stdout
        self.__capture_stream = None
        super(TestInfraLogging, self).setUp()

    def tearDown(self):
        if sys.stdout != self.__save_stdout:
            sys.stdout = self.__save_stdout

    def __start_capture(self):
        #self.__capture_stream = StringIO()
        sys.stdout = self.__capture_stream

    def __search_capture(self, thing_to_find, last=True):
        contents = self.__capture_stream.getvalue()
        self.assertTrue(thing_to_find in contents,
                        "Could not find '{0}' in log data '{1}'".format(thing_to_find, contents))
        if last:
            self.stdout = self.__save_stdout
            self.__capture_stream.close()
            self.__capture_stream = None

    def test_something(self):
        self.__start_capture()
        lg = logging.getLogger()
        lg.info('test_something')
        # todo: need to ACTUALLY highjack logs!
        #self.__search_capture('test_something')

    def test_infra_run(self):
        lg = getInfraRunLogger()
        lg.debug('getInfraRunLogger')

    def test_infra_run_over_info_5(self):
        lg = getInfraRunLogger()
        # should NOT show up!
        lg.debug_6('getInfraRunLogger -- debug_6')

    def test_infra_run_under_info_5(self):
        lg = getInfraRunLogger()
        lg.debug_4('getInfraRunLogger -- debug_4')

    def test_infra_data(self):
        lg = getInfraDataLogger()
        lg.debug('getInfraDataLogger')

    def test_test_run(self):
        lg = getTestRunLogger()
        lg.debug('getTestRunLogger')

    def test_test_data(self):
        lg = getTestDataLogger()
        lg.debug('getTestDataLogger')

    def test_infra_run_plus(self):
        lg = getInfraRunLogger('plus')
        lg.debug('checking infra.run.plus')

