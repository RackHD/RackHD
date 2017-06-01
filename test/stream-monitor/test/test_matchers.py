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

    def test_TC_test_error(self):
        self.assertRaisesRegexp(NameError,
                                "global name 'will_throw_an_error' is not defined$",
                                self.__get_inner_results)

    def test_TC_test_fail(self):
        self.assertRaisesRegexp(AssertionError, 'this_will_throw_a_fail$',
                                self.__get_inner_results)

    def test_TC_test_pass(self):
        iresult = self.__get_inner_results()
        self.assertEqual(iresult, 'I_passed!!!',
                         "expected 'I_passed!!!' got '{0}'".format(iresult))

    def __assert_basic_results(self, ok, oks=1, errs=0):
        iresult = self.__get_inner_results()
        if ok:
            iresult.assert_errors(self)
        self.assertEqual(iresult.is_ok, ok,
                         'is_ok was {0} not expected {1}'.format(iresult.is_ok, ok))
        self.assertEqual(
            iresult.had_errors, (not ok),
            'had_errors was {0} not expected {1}'.format(iresult.had_errors, not ok))
        self.assertEqual(
            iresult.ok_count, oks,
            'ok_count was {0} not expected {1}'.format(iresult.ok_count, oks))
        self.assertEqual(
            iresult.error_count, errs,
            'error_count was {0} not expected {1}'.format(iresult.error_count, errs))
        return iresult

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
        mrtre = re.compile('''\sMatch result type '(?P<result_type>.*?)',''')
        found_mrt = []
        for match in mrtre.finditer(tes):
            found_mrt.append(match.group('result_type'))
        self.assertListEqual(match_results, found_mrt, 'expected match-types != found')

    def test_match_single(self):
        """test that a single simple matcher:match is successful"""
        self.__assert_basic_results(ok=True, oks=1, errs=0)

    def test_overmatch(self):
        """test double match on singler matcher generates error"""
        ires = self.__assert_basic_results(ok=False, oks=1, errs=1)
        self.__test_error_asserts(
            ires, fails=1, matchers=3, events=['ook'],
            match_results=['MatcherOverMatch'])

    def test_zero_vs_one_undermatch(self):
        """test no matches on a required one match generates error"""
        ires = self.__assert_basic_results(ok=False, oks=0, errs=1)
        self.__test_error_asserts(
            ires, fails=1, matchers=1, events=['finish'],
            match_results=['MatcherUnderMatch'])

    def test_any_order_first_first(self):
        """test any-order group works with 1st than 2nd match"""
        ires = self.__assert_basic_results(ok=True, oks=2, errs=0)
        ires.assert_errors(self)    # should have none

    def test_any_order_2nd_first(self):
        """test any-order group works with 1st than 2nd match"""
        ires = self.__assert_basic_results(ok=True, oks=2, errs=0)
        ires.assert_errors(self)    # should have none

    def test_ordered_works_single(self):
        """test in-order group works with single match"""
        ires = self.__assert_basic_results(ok=True, oks=1, errs=0)
        ires.assert_errors(self)    # should have none

    def test_ordered_works_double(self):
        """test in-order group works with double match"""
        ires = self.__assert_basic_results(ok=True, oks=2, errs=0)
        ires.assert_errors(self)    # should have none

    def test_ordered_out_of_order_double(self):
        """test in-order group fails with out-of-order double match"""
        ires = self.__assert_basic_results(ok=False, oks=0, errs=3)
        self.__test_error_asserts(
            ires, fails=3, matchers=3,
            events=['m2', 'm1', 'finish'],
            match_results=['MatcherOrderedMissMatch', 'MatcherOrderedMissMatch', 'MatcherUnderMatch'])

    def test_ordered_full_miss(self):
        """test in-order group with full-miss set ignores an unmatched event"""
        ires = self.__assert_basic_results(ok=True, oks=2, errs=0)
        ires.assert_errors(self)    # should have none

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

            def setUp(self):
                """
                Most of these tests use the self-test stream monitor, so get it now.
                """
                self.__stsm = smp_get_stream_monitor('self-test')

            # Can I 1:! map each of these to a check routine up there? ^^^
            def test_TC_test_error(self):
                # Self-check of tester-class to check errors are seen
                this = will_throw_an_error  # NOQA: undefined name

            def test_TC_test_fail(self):
                # Self-check of tester-class to check fail (self.asserts) are seen
                self.assertFalse(True, 'this_will_throw_a_fail')

            def test_TC_test_pass(self):
                # Self-check of tester-class to check if pass is seen
                return 'I_passed!!!'

            def test_match_single(self):
                self.__stsm.match_single('ook', 'check that monkey said something')
                self.__stsm.inject('ook')
                results = self.__stsm.finish()
                return results

            def test_overmatch(self):
                self.__stsm.match_single(
                    'ook', 'check that the monkey said only only one thing')
                self.__stsm.inject('ook')
                self.__stsm.inject('ook')
                results = self.__stsm.finish()
                return results

            def test_zero_vs_one_undermatch(self):
                self.__stsm.match_single('ook', 'speak no evil')
                results = self.__stsm.finish()
                return results

            def test_any_order_first_first(self):
                self.__stsm.match_single('m1', 'will match first')
                self.__stsm.match_single('m2', 'will match second')
                self.__stsm.inject('m1')
                self.__stsm.inject('m2')
                results = self.__stsm.finish()
                return results

            def test_any_order_2nd_first(self):
                self.__stsm.match_single('m1', 'will match first')
                self.__stsm.match_single('m2', 'will match second')
                self.__stsm.inject('m2')
                self.__stsm.inject('m1')
                results = self.__stsm.finish()
                return results

            def test_ordered_works_single(self):
                self.__stsm.open_group(ordered=True)
                self.__stsm.match_single('m1', 'will match first')
                self.__stsm.inject('m1')
                self.__stsm.close_group()
                results = self.__stsm.finish()
                return results

            def test_ordered_works_double(self):
                self.__stsm.open_group(ordered=True)
                self.__stsm.match_single('m1', 'will match first')
                self.__stsm.match_single('m2', 'will match second')
                self.__stsm.inject('m1')
                self.__stsm.inject('m2')
                self.__stsm.close_group()
                results = self.__stsm.finish()
                return results

            def test_ordered_out_of_order_double(self):
                self.__stsm.open_group(ordered=True)
                self.__stsm.match_single('m1', 'will match first')
                self.__stsm.match_single('m2', 'will match second')
                self.__stsm.inject('m2')
                self.__stsm.inject('m1')
                self.__stsm.close_group()
                results = self.__stsm.finish()
                return results

            def test_ordered_full_miss(self):
                self.__stsm.open_group(ordered=True)
                self.__stsm.match_single('m1', 'will match first')
                self.__stsm.match_single('m2', 'will match second')
                self.__stsm.inject('m1')
                self.__stsm.inject('allowed_miss')
                self.__stsm.inject('m2')
                self.__stsm.close_group()
                results = self.__stsm.finish(allow_complete_miss=True)
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
        return [TC(self, self._testMethodName, 'runTests')]
