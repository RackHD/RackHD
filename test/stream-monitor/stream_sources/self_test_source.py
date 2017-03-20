"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

A set of super-simple matchers to use to self-test the matching framework.
"""
import sys
from .monitor_abc import StreamMonitorBaseClass
from .stream_matchers_base import StreamMatchBase


class _SelfTestMatcher(StreamMatchBase):
    """
    Implementation of a StreamMatchBase matcher that checks for simple text equality.
    """
    def __init__(self, match_text, description, min=1, max=1):
        self.__match_text = match_text
        super(_SelfTestMatcher, self).__init__(description, min=min, max=max)

    def _match(self, other_text):
        return other_text == self.__match_text

    def dump(self, ofile=sys.stdout, indent=0):
        super(_SelfTestMatcher, self).dump(ofile=ofile, indent=indent)
        ins = ' ' * indent
        print >>ofile, "{0} match_text='{1}'".format(ins, self.__match_text)


class SelfTestStreamMonitor(StreamMonitorBaseClass):
    """
    Implementation of a StreamMonitorBaseClass that does simple direct text matching.
    """
    @classmethod
    def enabled_for_nose(true):
        return True

    def match_single(self, match_val, description=None):
        """
        Add a matcher to this monitor.
        """
        if description is None:
            description = "match_single({0})".format(match_val)
        m = _SelfTestMatcher(match_val, description, 1, 1)
        self._add_matcher(m)

    def inject(self, text):
        """
        Allows manual injections of 'events' (in this case, simple text)
        """
        self._add_event(text)
