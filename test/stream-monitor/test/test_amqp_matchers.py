"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Self-test of the matcher infrastructure. This is less about individual matchers,
and more about if the various sequences and groups work (and fail!) as expected.
"""
from __future__ import print_function
import unittest
import plugin_test_helper
import inspect
import uuid
import traceback
import re
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


class TestMatcherGroups(plugin_test_helper.resolve_no_verify_helper_class()):
    """
    This is the test-container for the stream-monitor matchers.

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
            # specific test, then it will show up nicely in capture.
            iresult.dump_exception()
            raise iresult.results
        return iresult.results

    def __get_prerun_results(self):
        iresult = self.test_suite_results['test_pre_run']

        # if it was an assertion, throw it again (allow self.Raises and such)
        if iresult.is_exception:
            # dump the traceback to stdout. If the exception is caught by the
            # specific test, then it will show up nicely in capture.
            iresult.dump_exception()
            raise iresult.results
        self.__assert_a_basic_result(iresult.results[0], True, 5, 0)
        return iresult.results

    def __assert_a_basic_result(self, run_result, ok, oks, errs):
        if ok:
            run_result.assert_errors(self)

        self.assertEqual(run_result.is_ok, ok,
                         'is_ok was {0} not expected {1}'.format(run_result.is_ok, ok))
        self.assertEqual(
            run_result.had_errors, (not ok),
            'had_errors was {0} not expected {1}'.format(run_result.had_errors, not ok))
        self.assertEqual(
            run_result.ok_count, oks,
            'ok_count was {0} not expected {1}'.format(run_result.ok_count, oks))
        self.assertEqual(
            run_result.error_count, errs,
            'error_count was {0} not expected {1}'.format(run_result.error_count, errs))

    def __assert_basic_results(self, ok, oks=1, errs=0):
        iresult = self.__get_inner_results()
        self.__assert_a_basic_result(iresult, ok, oks, errs)
        return iresult

    def __assert_basic_multi_results(self, check_map):
        check_set = set(check_map.keys())
        ires_dict = self.__get_inner_results()
        ires_set = set(ires_dict.keys())
        self.assertSetEqual(
            check_set, ires_set,
            'the list of monitor names {} does not match what test returned {}'.format(check_set, ires_set))
        for check_name, cv in check_map.items():
            self.__assert_a_basic_result(ires_dict[check_name],
                                         cv['ok'], cv['oks'], cv['errs'])
        return ires_dict

    def __test_error_asserts(self, inner_results, fails, matchers, events, match_results):
        """
        Spot check of assert_errors from results:
        * make sure an error is thrown
        * make sure fails/matchers count is expected
        * make sure events occured in right order
        * make sure match-results types occured in right order
        """
        with self.assertRaises(AssertionError) as cm:
            inner_results.assert_errors(self)

        the_exception = cm.exception
        tes = str(the_exception)
        # Start by checking the failures and matchers counts were what we expected
        count_match = 'Asynch stream matchers encountered {0} failures out of {1} matchers'.format(
            fails, matchers)
        self.assertRegexpMatches(tes, count_match, 'incorrect failures/matchers')
        # Now make sure we had all the events in the right order
        ere = re.compile(r'''Matched \d+ matchers on event:$\s+'(?P<event_txt>.*)'$''',
                         re.MULTILINE)
        found_events = []
        for match in ere.finditer(tes):
            found_events.append(match.group('event_txt'))
        self.assertListEqual(events, found_events, 'events expected != found')

        # And finally look for the 'Match result type' lines show up in the expected order
        mrtre = re.compile('''Match result type '(?P<result_type>.*?)',''')
        found_mrt = []
        for match in mrtre.finditer(tes):
            found_mrt.append(match.group('result_type'))
        self.assertListEqual(match_results, found_mrt, 'expected match-types != found')

    def test_replay_of_five(self):
        self.__get_prerun_results()
        check_set = {
            'on-events-tracker1': {'ok': True, 'oks': 5, 'errs': 0},
        }
        self.__assert_basic_multi_results(check_set)

    def test_replay_of_five_plus_one_after(self):
        self.__get_prerun_results()
        check_set = {
            'on-events-tracker1': {'ok': True, 'oks': 6, 'errs': 0},
        }
        self.__assert_basic_multi_results(check_set)

    def test_dont_replay_of_five(self):
        check_set = {
            'on-events-tracker1': {'ok': True, 'oks': 0, 'errs': 0},
        }
        self.__assert_basic_multi_results(check_set)

    def test_dual_match_single(self):
        """test two processesor pointing at the same tracker both report success"""
        check_set = {
            'on-events-tracker1': {'ok': True, 'oks': 6, 'errs': 0},
            'on-events-tracker2': {'ok': True, 'oks': 1, 'errs': 0},
        }
        self.__assert_basic_multi_results(check_set)

    def makeSuite(self):
        class TC(unittest.TestCase):
            """testme testme testme"""
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

            @classmethod
            def setUpClass(cls):
                cls._amqp_sp = smp_get_stream_monitor('amqp')
                cls._on_events_tracker = cls._amqp_sp.create_tracker('abc-tracker', 'on.events', 'on.events.tests')

            def setUp(self):
                """
                Most of these tests use the self-test stream monitor, so get it now.
                """
                self.__amqp_sm = smp_get_stream_monitor('amqp')
                self.__test_payloads = []
                for inx in range(10):
                    self.__test_payloads.append({'payload_index': inx, 'test_uuid': str(uuid.uuid4())})

            def test_pre_run(self):
                """
                makeSuite will put this test in the list, then the name-matched one, thus allowing
                pre-setup of the recorder mode
                """
                qp1 = self.__amqp_sm.get_tracker_processor(self._on_events_tracker)
                qp1.match_any(min=5, max=10)
                self.__amqp_sm.inject('on.events', 'on.events.tests', self.__test_payloads[0])
                self.__amqp_sm.inject('on.events', 'on.events.tests', self.__test_payloads[1])
                self.__amqp_sm.inject('on.events', 'on.events.tests', self.__test_payloads[2])
                self.__amqp_sm.inject('on.events', 'on.events.tests', self.__test_payloads[3])
                self.__amqp_sm.inject('on.events', 'on.events.tests', self.__test_payloads[4])
                results = self.__amqp_sm.finish()
                return results

            def test_replay_of_five(self):
                qp1 = self.__amqp_sm.get_tracker_processor(self._on_events_tracker)
                qp1.match_any(min=5, max=10)
                fin_list = self.__amqp_sm.finish()
                results = {
                    'on-events-tracker1': fin_list[0]
                }
                return results

            def test_replay_of_five_plus_one_after(self):
                qp1 = self.__amqp_sm.get_tracker_processor(self._on_events_tracker)
                qp1.match_any(min=6, max=10)
                self.__amqp_sm.inject('on.events', 'on.events.tests', self.__test_payloads[5])
                fin_list = self.__amqp_sm.finish()
                results = {
                    'on-events-tracker1': fin_list[0]
                }
                return results

            def test_dont_replay_of_five(self):
                qp1 = self.__amqp_sm.get_tracker_processor(self._on_events_tracker, start_at='now')
                qp1.match_any(min=0, max=0)
                fin_list = self.__amqp_sm.finish()
                results = {
                    'on-events-tracker1': fin_list[0]
                }
                return results

            def test_dual_match_single(self):
                # create 1 processor that will consume the 5 existing items from the tracker plus a real one
                qp1 = self.__amqp_sm.get_tracker_processor(self._on_events_tracker)
                qp1.match_any(min=6, max=10)
                # create a 2nd processor on the same tracker that will ONLY consume the one new item
                qp2 = self.__amqp_sm.get_tracker_processor(self._on_events_tracker, start_at='now')
                qp2.match_any(min=1, max=1)

                self.__amqp_sm.inject('on.events', 'on.events.tests', self.__test_payloads[5])
                fin_list = self.__amqp_sm.finish()
                results = {
                    'on-events-tracker1': fin_list[0],
                    'on-events-tracker2': fin_list[1]
                }
                return results

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
        return[
            TC(self, "test_pre_run", 'runTests'),
            TC(self, self._testMethodName, 'runTests')
        ]
