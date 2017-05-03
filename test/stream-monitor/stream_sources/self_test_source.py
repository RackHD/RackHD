"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

A set of super-simple matchers to use to self-test the matching framework.
"""
import sys
import gevent
import gevent.queue
import uuid
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

    def handle_start_test(self, test):
        """
        called at stream-monitor start-test. We need to create a little relay
        greenlet so that calling our "inject" method can be async from
        processing. Basically, other monitors will be calling _add_event from
        a greenlet and if we don't, there are some queue drains that think
        they will block forever.
        """
        self.__relay_queue = gevent.queue.Queue()
        self.__relay_greenlet = gevent.spawn(self.__relay_greenlet_main)
        self.__relay_greenlet.greenlet_name = 'self-test-sm-relay-gl'  # allow flogging to print nice name

        super(SelfTestStreamMonitor, self).handle_start_test(test)

    def handle_stop_test(self, test):
        """
        shutdown the little relay thing
        """
        self.__relay_queue.put('DONE-SPECIAL-MESSAGE')
        gevent.wait([self.__relay_greenlet])

    def __relay_greenlet_main(self):
        gevent.sleep(0)
        while True:
            msg = self.__relay_queue.get()
            self._add_event(msg)
            if msg.startswith('DONE-SPECIAL-MESSAGE'):
                break

    def inject(self, text):
        """
        Allows manual injections of 'events' (in this case, simple text)
        """
        self.__relay_queue.put(text)

    def test_helper_send_end_event(self):
        """
        Sends a very specifc event to indicate an end-of-test.
        """
        msg = 'DONE-SPECIAL-MESSAGE-{}'.format(str(uuid.uuid4()))
        self.inject(msg)
        return msg
