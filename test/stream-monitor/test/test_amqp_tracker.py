"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Self-test of the matcher infrastructure. This is less about individual matchers,
and more about if the various sequences and groups work (and fail!) as expected.
"""
from __future__ import print_function
import unittest
import plugin_test_helper
import inspect
import traceback
import uuid
import json
from sm_plugin import smp_get_stream_monitor


class _InnerResults(object):
    def __init__(self, results_obj, exception_str=None):
        self.__exception_str = exception_str
        self.results = results_obj

    @property
    def is_exception(self):
        return isinstance(self.results, Exception)

    def dump_exception(self):
        if self.__exception_str is not None:
            for line in self.__exception_str.split('\n'):
                print(line)


class TestAMQPOnDemand(plugin_test_helper.resolve_no_verify_helper_class()):
    """
    This is the test-container for the stream-monitor amqp trackers

    This is a nose-plugin tester based test-container, which means that makeSuite is
    called once for each "test_xxxx" method in this class and returns a list of
    test-cases to run. Each of those is run _within_ the context of its own complete
    nose environment (complete with the plugin(s) we are testing!) , and then the
    "test_xxxx" method is called.

    This, however, means one normally needs to make a complete class for each test case,
    since if you don't, all the test-cases from makeSuite get called once for each
    outer test-case. Also, errors from the makeSuite test cases are not reported
    directly to the outer-context, which means test counts and such would be off.

    To streamline this a little, makeSuite "peeks" at the outer test-name and only
    returns a single test-case containing the inner-test-case for the exact same name.
    It also passes the outer-test-case into the inner own so that it can set its
    results into TestMatcherGroups.test_suite_result['test_name_xxxx'], allowing the
    outer tests to do the work of looking at results, while the inner ones just do
    the sequencing.
    """
    test_suite_results = {}
    args = ['--sm-amqp-url', 'on-demand']
    longMessage = True   # this turns on printing of arguments for unittest.assert*s

    def __get_inner_results(self):
        our_frame = inspect.currentframe()
        # climb looking for the first thing starting with 'test_'. We
        # could just pop one up, but that would make things like
        # self.assertRaises() fail.
        while our_frame is not None and not our_frame.f_code.co_name.startswith('test_'):
            our_frame = our_frame.f_back
        assert our_frame is not None, \
            "alleged impossible situation where no 'test_' was found in stack"

        # get our callers name
        parent_name = our_frame.f_code.co_name

        # now fetch results put there by the method with the same name
        # inside a TC from makeSuite() below.
        iresult = self.test_suite_results[parent_name]

        # if it was an assertion, throw it again (allow self.Raises and such)
        if iresult.is_exception:
            # dump the traceback to stdout. If the exception is caught by the
            # specific test, then it will show up nicely in capture. Unless it's
            # a unitest.SkipTest, in which case we don't want to dump the backtrace!
            if not isinstance(iresult.results, unittest.SkipTest):
                iresult.dump_exception()
            raise iresult.results
        return iresult.results

    def test_connected_to_ondemand_server(self):
        ires = self.__get_inner_results()
        self.assertIsInstance(ires, bool, 'return type must be boolean')
        self.assertTrue(ires, 'was not connected to amqp server')

    def test_send_receive_sync_message(self):
        ires = self.__get_inner_results()
        expected = ires['expected']
        got = ires['got']
        self.assertIsNotNone(got, "message never received")
        di = got.delivery_info
        self.assertEqual(di['routing_key'], expected['route_key'])
        body = json.loads(got.body)
        self.assertEqual(body['test_uuid'], expected['payload']['test_uuid'])

    def test_send_receive_async_message(self):
        ires = self.__get_inner_results()
        expected = ires['expected']
        got = ires['got']
        self.assertIsNotNone(got, "message never received")
        di = got.msg.delivery_info
        self.assertEqual(di['routing_key'], expected['route_key'])
        body = got.body
        self.assertEqual(body['test_uuid'], expected['payload']['test_uuid'])
        print("di={}".format(di))
        print("body={}".format(body))

    def makeSuite(self):
        class TC(unittest.TestCase):
            def __init__(self, owner, test_method_name, *args, **kwargs):
                self.__owner = owner
                self.__this_method_this_time = test_method_name
                super(TC, self).__init__(*args, **kwargs)

            def shortDescription(self):
                return self.__this_method_this_time

            def __str__(self):
                return '{0} ({1})'.format(
                    self.__this_method_this_time,
                    unittest.util.strclass(self.__class__))

            def setUp(self):
                """
                Note: exceptions throw in setup are caught by
                TestCase, and seem to bypass our return flow.
                """
                self.__asm = smp_get_stream_monitor('amqp')

            def __skip_no_amqp(self):
                if not self.__asm.has_amqp_server:
                    raise unittest.SkipTest('Skipping AMQP test because no AMQP server defined')

            def test_connected_to_ondemand_server(self):
                self.__skip_no_amqp()
                results = self.__asm.test_helper_is_amqp_running()
                return results

            def test_send_receive_sync_message(self):
                self.__skip_no_amqp()
                payload = {'test_uuid': str(uuid.uuid4())}
                queue = self.__asm.test_helper_sync_send_msg(
                    'on.events', 'on.events', 'on.events.test', payload)
                data_back = self.__asm.test_helper_sync_recv_msg(queue)
                return {'expected': {'route_key': 'on.events.test', 'payload': payload},
                        'got': data_back}

            def test_send_receive_async_message(self):
                self.__skip_no_amqp()
                on_events_tracker = self.__asm.create_tracker('on-events-tsram', 'on.events', 'on.events.tests')
                payload = {'test_uuid': str(uuid.uuid4())}
                self.__asm.inject('on.events', 'on.events.tests', payload)
                what_sent = {'route_key': 'on.events.tests', 'payload': payload}

                tracker_record = on_events_tracker.test_helper_wait_for_one_message(timeout=100)
                expected = {
                    'expected': what_sent,
                    'got': tracker_record
                }
                return expected

            def runTests(self):
                method_set = inspect.getmembers(self, self.__check_for_usable_test)
                ran_one = False
                for method_name, method in method_set:
                    if method_name == self.__this_method_this_time:
                        self.__run_test(method_name, method)
                        ran_one = True
                        break
                assert ran_one, \
                    'Unable to find test-method matching {0}'.format(self.__this_method_this_time)

            def __run_test(self, method_name, method):
                results = None
                exception_str = None
                try:
                    results = method()
                except Exception as ex:
                    results = ex
                    exception_str = traceback.format_exc()

                results = _InnerResults(results, exception_str)

                self.__owner.test_suite_results[method_name] = results

            def __check_for_usable_test(self, item):
                if inspect.ismethod(item):
                    # ok, it's at least a method.
                    if item.__name__.startswith('test_'):
                        return True
                return False
        return [TC(self, self._testMethodName, 'runTests')]
