"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This file holds a base class information for writing a stream-monitor. It is
intended to provide life-cycle and common grouping methods. It works items
derived from the classes in stream_matcher_base and stream_matchers_results to
manage stream-based-pattern matching.
"""
import gevent
import gevent.queue
import time
from .stream_matchers_base import StreamGroupsRoot, StreamGroupsOrdered, StreamGroupsUnordered
from .stream_matchers_results import StreamRunResults


class StreamMonitorBaseClass(object):
    def __init__(self):
        """
        Setup the basic state. An implementation for a specific monitor must
        be a stream-monitor plugin so that the methods are called at the proper
        times.
        """
        self.__in_test = None
        self._match_groups = None
        self.__group_stack = None
        self.__seen_before_test = gevent.queue.Queue()
        self.__seen_during_test = gevent.queue.Queue()

    def handle_set_flogging(self, logs):
        self._logs = logs
        self._logs.debug('handling pluggin progression for %s logs=%s', self, logs)

    def handle_begin(self):
        """
        called at stream-monitor plugin begin. We create a matchgroup and
        group stacks. (See 'push_group' for info on groups)

        At this time, we only support "seeing" things _during_ a test. The
        '__in_test' state was put in here to help me think about how to possibly
        structure things when/if phasing gets added.
        """
        self._logs.debug('handle_begin pluggin progression for %s', self)
        self._match_groups = StreamGroupsRoot()
        self.__group_stack = [self._match_groups]
        self.__in_test = None

    @property
    def in_test(self):
        """
        Return a nose test case for being somewhere in this test, or None if outside
        """
        return self.__in_test

    def handle_start_test(self, test):
        """
        called at stream-monitor start-test. Pass on the start-test to the main
        group and clear the evens we have "seen".
        """
        self._logs.debug('handle_start_test pluggin progression for %s test=%s', self, test)
        self._match_groups.handle_start_test(test)
        self.__seen_before_test = gevent.queue.Queue()
        self.__seen_during_test = gevent.queue.Queue()
        self.__in_test = test

    def handle_stop_test(self, test):
        """
        called at stream-monitor stop-test.
        """
        self._logs.debug('handle_stop_test pluggin progression for %s test=%s', self, test)

    def handle_after_test(self, test):
        """
        called at stream-monitor after-test
        """
        self._logs.debug('handle_after_test pluggin progression for %s test=%s', self, test)
        self.__in_test = None

    def _add_matcher(self, matcher):
        """
        sub-class callable method to add a matcher to the current group
        """
        current = self.__group_stack[-1]
        current.add_matcher(matcher)

    def _add_event(self, event_data):
        """
        sub-class callable method to add an event to what we have "seen".
        """
        self._logs.debug('adding event. in_test=%s, event_data=%s', self.__in_test, event_data)
        if self.__in_test:
            self.__seen_during_test.put(event_data)
        else:
            self.__seen_before_test.put(event_data)

    def push_group(self, ordered=False):
        """
        This is "take one" at groups of matchers. The root level group is an
        "unordered" group, and thus any matchers added to it can be matched in
        any order. From there, additional ordered or unordered groups can be
        pushed into this class to build up and/or combinations. This really is
        just a basic set at this point until more data comes in on common use-styles.

        The __group_stack property keeps track of our current depth.
        """
        if ordered:
            ng = StreamGroupsOrdered()
        else:
            ng = StreamGroupsUnordered()

        current = self.__group_stack[-1]
        current.add_group(ng)
        self.__group_stack.append(ng)

    def pop_group(self):
        """
        The pop method to go with push_group. Basically sanity checks depth and
        handles moving "up" a level.
        """
        assert len(self.__group_stack) > 1, \
            'attempted to pop root group!'
        self.__group_stack = self.__group_stack[:-1]

    def test_helper_get_all_events(self, timeout=5, end_event=None, max_grab=None):
        """
        Goes and pulls all data from the event-queue and returns them.
        """
        rl = []
        sleep_till = time.time() + timeout
        ct = time.time()
        self._logs.irl.debug('going to try and get all events. timeout=%s, sleep_till=%s, max_grab=%s',
                             timeout, sleep_till, max_grab)
        while ct < sleep_till:
            try:
                self._logs.irl.debug_3('trying. ct=%s, left=%s, grabbed=%d', ct, sleep_till - ct, len(rl))
                event_data = self.__seen_during_test.get(block=False)
                self._logs.irl.debug_4('  end_event=%s, event=%s', end_event, event_data)
                if end_event is not None and end_event == event_data:
                    self._logs.irl.debug('  exiting loop because end-event %s seen', end_event)
                    break
                rl.append(event_data)
            except gevent.queue.Empty:
                pass
            ct = time.time()
            gevent.sleep(0)
            if max_grab is not None:
                if len(rl) >= max_grab:
                    break
        self._logs.irl.debug('return %d: %s', len(rl), rl)
        return rl

    def finish(self, timeout=5):
        """
        Called when data injection is complete and the events should be
        checked vs the matchers. This is primarily for self-tests.
        """
        assert len(self.__seen_before_test) == 0, 'not implemented yet'
        assert len(self.__group_stack) == 1, \
            'did not pop all pushed groups: {0}'.format(self.__group_stack)

        end_event = self.test_helper_send_end_event()

        results = StreamRunResults()

        events = self.test_helper_get_all_events(timeout=timeout, end_event=end_event)
        self._logs.irl.debug('get %d (%s) events.', len(events), events)
        for event_data in events:
            res = self._match_groups.check_event(event_data)
            results.add_result(res)
        res = self._match_groups.check_ending()
        results.add_result(res)
        return results
