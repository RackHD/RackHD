"""
Copyright 2017, EMC, Inc.

This is the base for the various stream matchers.
"""
import logging
from .stream_matchers_results import MatcherResult, MatcherUnderMatch, MatcherOverMatch, MatcherCleanHitResult
from .stream_matchers_results import MatcherOrderedMissMatch
import sys
try:
    from cStringIO import StringIO as _StringIO
except ImportError:
    from StringIO import StringIO as _StringIO
from pprint import PrettyPrinter

log = logging.getLogger('nose.plugins.stream_monitor.matchers')


class _IndentedPrettyPrinter(PrettyPrinter):
    """
    Utility extension of pretty printer to indent the entire
    output by a certain amount.
    """
    def __init__(self, per_line_indent=0, **kwargs):
        self.__per_line_indent_str = ' ' * per_line_indent
        PrettyPrinter.__init__(self, **kwargs)

    def pprint(self, object):
        rs = self.pformat(object)
        self._stream.write(rs)
        self._stream.write('\n')

    def pformat(self, object):
        fs = PrettyPrinter.pformat(self, object)
        rs = _StringIO()
        for line in fs.split('\n'):
            if len(line) != 0:
                rs.write(self.__per_line_indent_str)
                rs.write(line)
            rs.write('\n')
        return rs.getvalue()


class _MatcherBatcher(object):
    """
    Match-result batch container.

    There is one of these per event, with the various StreamGroups adding
    (matcher, result-of-trying-event-against-the-matcher) pairs via add_result.
    """
    def __init__(self, event_data):
        self.__saved_event_data = event_data
        self.__results_seen = []

    def add_result(self, matcher, result):
        """
        Adds a matcher (the object capable of trying to match the event) and the
        result of that attempt to this batch.

        Note that a 'result' can be another _MatcherBatcher when the matcher is a sub-group (like
        a an ordered-group inside of unordered-group).
        """
        if result is not None:
            assert isinstance(result, MatcherResult) or isinstance(result, _MatcherBatcher), \
                'result was {0}, not a required {1} or {2}'.format(
                result, MatcherResult, _MatcherBatcher)

        self.__results_seen.append((matcher, result))

    def __get_a_result_status(self, result):
        """
        Internal method to decode the error/ok state from the different
        types of results.

        returns (is_error, is_ok)
        """
        if result is None:
            return False, False
        elif isinstance(result, MatcherResult):
            return result.is_error, result.is_ok
        elif isinstance(result, _MatcherBatcher):
            return result.has_error, result.has_ok
        else:
            assert False, 'wrong type {0}'.format(result)

    def __get_result_statuses(self):
        """
        Iterator for getting the (is_error, is_ok) state for each result.
        """
        for _, result in self.__results_seen:
            is_error, is_ok = self.__get_a_result_status(result)
            yield is_error, is_ok

    @property
    def has_error(self):
        """
        Returns the composite "is_error" for the entire batch. If there
        are any results that are errors, the entire batch is.
        """
        for has_error, _ in self.__get_result_statuses():
            if has_error:
                return True
        return False

    @property
    def has_ok(self):
        """
        Returns if any part of this batch was "ok" (no error).
        """
        for _, has_ok in self.__get_result_statuses():
            if has_ok:
                return True
        return False

    @property
    def is_terminal(self):
        """
        Indicates if this batch is terminal or not. Since "terminal" only
        applies to a direct-matcher, we always return False.
        """
        return False

    def dump(self, ofile=sys.stderr, indent=0, is_sub_batch=False):
        """
        Method to dump our state for use in reporting a failed test.
        """
        ins = ' ' * indent
        indent += 2
        pp = _IndentedPrettyPrinter(per_line_indent=indent, stream=ofile)
        if is_sub_batch:
            print >>ofile, "{0}----matcher group's results".format(ins)
        else:
            print >>ofile, "{0}Matched {1} matchers on event:".format(ins, len(self.__results_seen))
            pp.pprint(self.__saved_event_data)
        inx = 0
        ins += ' '  # indent detail one more space.
        for matcher, result in self.__results_seen:
            inx += 1
            is_error, is_ok = self.__get_a_result_status(result)
            print >>ofile, "{0}result {1:02d} of {2:02d} is_error={3:5} is_ok={4:5}".format(
                ins, inx, len(self.__results_seen), str(is_error), str(is_ok))
            if is_sub_batch:
                print >>ofile, "{0} Matcher '{1}' (from group)".format(ins, matcher.description)
            else:
                matcher.dump(ofile, indent)
            if result is None:
                print >>ofile, "{0}result: not-matched(None)"
            elif isinstance(result, _MatcherBatcher):
                result.dump(ofile, indent, is_sub_batch=True)
            else:
                result.dump(ofile, indent)

        print >>ofile


class StreamMatchBase(object):
    """
    Base class for stream-matchers.

    It handles the common bits of match-ranges (I.E., "we can have between 2 and 5 of these")
    along with descriptions and common diagnostic output routines.

    A matcher is three 'matchable' states:
    1) Have not found enough matches yet for this to be ok (still_requires_match)
    2) Have found enough matches to be "ok", but have not gone over into overmatch.
    3) Still technically legal to match, but in overmatch. This last one is still a bit fuzzy
       and is more of a conceptual rather than literal state.
    """
    def __init__(self, description, min=1, max=1):
        self.__min = min
        self.__max = max
        self.__match_count = 0
        self.__overmatch = None
        self.__missmatch = None
        self.__still_matchable = True
        self.description = description

    def dump(self, ofile=sys.stdout, indent=0):
        """
        Method to dump our state for use in reporting a failed test.
        """
        ins = ' ' * indent
        print >>ofile, "{0}Matcher '{1}'".format(ins, self.description)
        print >>ofile, "{0} matched={1}, min={2}, max={3}".format(
            ins, self.__match_count, self.__min, self.__max),

        extra = []
        if self.__overmatch is not None:
            extra.append("overmatched={0}".format(self.__overmatch))
        if self.__missmatch is not None:
            extra.append("missmatch={0}".format(self.__missmatch))
        if len(extra) == 0:
            if self.__match_count >= self.__min and self.__match_count <= self.__max:
                extra.append("in-count-range")
            else:
                extra.append("out-of-range-but-not-marked-yet(count={0}, min={1}, max={2})".format(
                    self.__match_count, self.__min, self.__max))

        print >>ofile, ', '.join(extra)
        print >>ofile, "{0} still_matchable={1}, still_requires_match={2}".format(
            ins, self.is_still_matchable, self.still_requires_match)

    @property
    def is_still_matchable(self):
        """
        property to indicate if the matcher is still valid to check against.
        Currently this is not altered and always returns True.
        """
        return self.__still_matchable

    @property
    def still_requires_match(self):
        """
        Property to indicate that more matches are needed before the minimum count is hit.
        """
        return self.__match_count < self.__min

    def check_ending(self):
        """
        End-of-run check method. We check for if ending now causes this matcher to go
        invalid because it was not matched enough times.
        """
        if self.__match_count < self.__min:
            res = MatcherUnderMatch(
                self.description, self.__min, self.__max, self.__match_count)
        else:
            res = None
        return res

    def _match(self, other_thing):
        raise NotImplemented('subclass must implement this')

    def check_event(self, event_data, break_on_miss=False):
        """
        Method that does the grunt work of checking an event against this matcher
        and deals with all the possible error conditions.
        """
        # Step 1: see if the matcher even matches the event data!
        low_level_matched = self._match(event_data)
        if low_level_matched:
            # It did, so bump the match count
            self.__match_count += 1
            if self.__missmatch is not None:
                # We are already in a state where we are part of an ordered
                # set, and we matched something _beyond_ this one in that set.
                # (see break_on_miss below). We bump the count in the mismatch result
                # for diagnostic output.
                self.__missmatch.bump_matched()
                res = self.__missmatch
            elif self.__match_count > self.__max:
                # And we have matched too many. If we just went over the edge,
                # create an overmatch result, otherwise bump the count on the
                # one we already made.
                if self.__overmatch is None:
                    self.__overmatch = MatcherOverMatch(
                        self.description, self.__min, self.__max, self.__match_count)
                else:
                    self.__overmatch.adjust_count(self.__match_count)
                res = self.__overmatch
            else:
                # Yay! It's a match! Set the 'is_terminal' on it to "consume" the event (stops
                # further matching attempts)
                res = MatcherCleanHitResult(self.description, is_terminal=True)
        else:
            # So, it wasn't a match....
            if break_on_miss:
                # break_on_miss means we are part of an ordered set and we HAD to match. If
                # we were already broken, just bump the count otherwise create the mismatch instance.
                if self.__missmatch is None:
                    self.__missmatch = MatcherOrderedMissMatch(
                        self.description, self.__min, self.__max, self.__match_count)
                else:
                    self.__missmatch.bump_missed()
                res = self.__missmatch
            else:
                # We return None to indicate no match.
                res = None
        return res


class _StreamGroupsBase(object):
    """
    This is the base for groups of matchers. This base handles
    the common junk like diag dumps, and so on.

    Right now the matching system is limited to -during- the test
    itself.
    """
    def __init__(self, group_type):
        """
        param group_type is a string used to help show whats going on
        when dumping on errors.
        """
        self._in_test_matchers = []
        self.__group_type = group_type

    def dump(self, ofile=sys.stdout, indent=0):
        """
        Method to dump our state for use in reporting a failed test.
        """
        ins = ' ' * indent
        mcount = 0
        gcount = 0
        for m in self._in_test_matchers:
            if isinstance(m, StreamMatchBase):
                mcount += 1
            elif isinstance(m, _StreamGroupsBase):
                gcount += 1
            else:
                assert False, 'matcher in list that is neither matcher or group {0}'.format(m)

        print >>ofile, "{0}{1} group of {2} matchers ({3} direct-matchers, {4} sub-groups) is_still_matchable={5})".format(
            ins, self.__group_type, len(self._in_test_matchers), mcount, gcount, self.is_still_matchable)
        indent += 2
        for m in self._in_test_matchers:
            m.dump(ofile, indent)

    def handle_start_test(self, test):
        """
        Clear out the matchers that have been pushed in when the test starts.
        """
        self._in_test_matchers = []

    @property
    def is_still_matchable(self):
        """
        If any matcher in our list is still matchable, so are we.
        """
        for m in self._in_test_matchers:
            if m.is_still_matchable:
                return True
        return False

    def add_matcher(self, matcher):
        """
        Add a single matcher to the group.
        """
        assert isinstance(matcher, StreamMatchBase), \
            'matcher {0} must be a {1} but was a {2}'.format(matcher, StreamMatchBase, type(matcher))
        self._in_test_matchers.append(matcher)

    def add_group(self, group):
        """
        Add an entire group of matchers to this group.
        """
        assert isinstance(group, _StreamGroupsBase), \
            '{0} must be a {1}'.format(group, _StreamGroupsBase)
        self._in_test_matchers.append(group)

    def check_ending(self):
        """
        Called by stream-monitor at end-of-test
        """
        match_batch = _MatcherBatcher('finish')
        for matcher in self._in_test_matchers:
            res = matcher.check_ending()
            if res is not None:
                match_batch.add_result(matcher, res)
        return match_batch


class StreamGroupsOrdered(_StreamGroupsBase):
    """
    Ordered set of matchers.
    """
    def __init__(self):
        super(StreamGroupsOrdered, self).__init__('ordered/sequence')

    def check_event(self, event_data):
        """
        Implement the event-check logic for an ordered group. "Ordered" means that each matcher added
        has to be hit in sequence. For example, we can create a group that says "A then B",
        and if we see event-type B before A, we will error.

        This gets a little more tricky when we set up something like "between 1 and 4 A, then B", since
        the following scenarios exist:
        * AB, AAB, AAAB, AAAAB -> all valid
        * B -> out-of-order
        * ABA -> out-of-order because even though the 'A' matcher could consume up to three more, once we "moved past it" by
            hitting the 'B', the 'A' matcher has to be disabled.
        """
        match_batch = _MatcherBatcher(event_data)
        for matcher in self._in_test_matchers:
            if matcher.still_requires_match:
                # MUST match
                res = matcher.check_event(event_data, break_on_miss=True)
                match_batch.add_result(matcher, res)
                return match_batch
            elif matcher.is_still_matchable:
                # CAN match, but it's ok if it doesn't.
                # todo: need to add 'lock' once something -past- this point
                #  matches.
                res = matcher.check_event(event_data)
                if res is not None:
                    match_batch.add_result(matcher, res)
                    return match_batch

        return match_batch


class StreamGroupsUnordered(_StreamGroupsBase):
    """
    Unordered set of matchers.
    """
    def __init__(self):
        super(StreamGroupsUnordered, self).__init__('unordered')

    def check_event(self, event_data):
        """
        Implement the event-check logic for an unordered group. "Unordered" means that
        while each matcher is tried in order they were added until one matches.
        """
        match_batch = _MatcherBatcher(event_data)
        for matcher in self._in_test_matchers:
            if matcher.is_still_matchable:
                res = matcher.check_event(event_data)
                match_batch.add_result(matcher, res)
                if res is not None and res.is_terminal:
                    return match_batch

        return match_batch


class StreamGroupsRoot(StreamGroupsUnordered):
    pass
