"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This file holds a base class information for writing a stream-monitor. It is
intended to provide life-cycle and common grouping methods. It works items
derived from the classes in stream_matcher_base and stream_matchers_results to
manage stream-based-pattern matching.
"""

from .stream_matchers_base import StreamGroupsRoot, StreamGroupsOrdered, StreamGroupsUnordered
from .stream_matchers_results import StreamRunResults


class StreamMonitorBaseClass(object):
    def __init__(self):
        """
        Setup the basic state. An implementation for a specific monitor must
        be a stream-monitor plugin so that the methods are called at the proper
        times.
        """
        self._in_test = False
        self.__match_groups = None
        self.__group_stack = None
        self.__seen_before_test = []
        self.__seen_during_test = []

    def handle_begin(self):
        """
        called at stream-monitor plugin begin. We create a matchgroup and
        group stacks. (See 'push_group' for info on groups)

        At this time, we only support "seeing" things _during_ a test. The
        '__in_test' state was put in here to help me think about how to possibly
        structure things when/if phasing gets added.
        """
        self.__match_groups = StreamGroupsRoot()
        self.__group_stack = [self.__match_groups]
        self.__in_test = False

    def handle_start_test(self, test):
        """
        called at stream-monitor start-test. Pass on the start-test to the main
        group and clear the evens we have "seen".
        """
        self.__match_groups.handle_start_test(test)
        self.__seen_before_test = []
        self.__seen_during_test = []
        self.__in_test = True

    def handle_stop_test(self, test):
        """
        called at stream-monitor stop-test.
        """
        self.__in_test = False

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
        if self.__in_test:
            self.__seen_during_test.append(event_data)
        else:
            self.__seen_before_test.append(event_data)

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

    def finish(self):
        """
        Called when data injection is complete and the events should be
        checked vs the matchers. This is primarily for self-tests.
        """
        assert len(self.__seen_before_test) == 0, 'not implemented yet'
        assert len(self.__group_stack) == 1, \
            'did not pop all pushed groups: {0}'.format(self.__group_stack)

        results = StreamRunResults()
        for event_data in self.__seen_during_test:
            res = self.__match_groups.check_event(event_data)
            results.add_result(res)

        res = self.__match_groups.check_ending()
        results.add_result(res)
        return results
