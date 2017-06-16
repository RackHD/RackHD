"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import copy
import sys
from StringIO import StringIO


class StreamRunResults(object):
    """
    Composite of results information from a specific run
    """
    def __init__(self):
        self.__all_res_list = []
        self.__ok_res_list = []
        self.__error_res_list = []

    def add_result(self, result):
        self.__all_res_list.append(result)
        if result.has_error:
            self.__error_res_list.append(result)
        elif result.has_ok:
            self.__ok_res_list.append(result)
        # The 'else' here would basically be an empty result

    @property
    def had_errors(self):
        return len(self.__error_res_list) > 0

    @property
    def is_ok(self):
        return len(self.__error_res_list) == 0

    @property
    def ok_count(self):
        return len(self.__ok_res_list)

    @property
    def error_count(self):
        return len(self.__error_res_list)

    def get_error_list(self):
        return copy.copy(self.__error_res_list)

    def assert_errors(self, testcase, comment=None):
        """
        Utility routine to generate a single big unittest failure built
        from the errors-list.

        Note, you can also use get_error_list() and do your own.
        """
        if len(self.__error_res_list) == 0:
            return  # no errors, no need to fail the test!
        if comment is None:
            comment = ""
        fs = StringIO()
        print >>fs, "Asynch stream matchers encountered {0} failures out of {1} matchers {2}".format(
            len(self.__error_res_list), len(self.__all_res_list), comment)
        print >>fs
        for er in self.__error_res_list:
            er.dump(fs, 2)

        testcase.fail(fs.getvalue())

    def dump(self, ofile=sys.stdout, indent=0):
        if ofile is None:
            ofile = StringIO()
            rstring = True
        else:
            rstring = False

        for n in self.__all_res_list:
            n.dump(ofile=ofile, indent=indent + 2)
        if rstring:
            return ofile.getvalue()

    def __str__(self):
        rs = 'results(ok={0},error={1})'.format(len(self.__ok_res_list),
                                                len(self.__error_res_list))
        return rs

    def __repr__(self):
        return str(self)


class MatcherResult(object):
    """
    Base class for all match-results. The interesting properties are:
      is_error : there was a match failure of some sort. For example, a matcher was
          set up to match between 1 and 3 times and 4 matching events were seen.
      is_terminal : true if the given match should terminate event processing. For example,
          an overmatch (matched 4 times, but expected between 1 and 3) is terminal, since
          the event was "consumed" in generating the overmatch. A clean miss, however, is
          not terminal, since outside of an ordered group, more matches can attempted.
      is_ok : currently just !is_error
    """
    def __init__(self, description, used_for, is_error, is_terminal):
        self.description = description
        self.__used_for = used_for
        self.is_error = is_error
        self.is_terminal = is_terminal
        if self.is_error:
            self.is_ok = False
        else:
            self.is_ok = True

    def _update_description(self, new_description):
        self.description = new_description

    def dump(self, ofile=sys.stdout, indent=0):
        ins = ' ' * indent
        print >>ofile, "{0}Match result type '{1}', description='{2}'".format(
            ins, self.__class__.__name__, self.description)
        print >>ofile, "{0} this match-result is used for {1}".format(ins, self.__used_for)
        print >>ofile, "{0} is_error={1}, is_terminal={2}, is_ok={3}".format(
            ins, str(self.is_error), str(self.is_terminal), str(self.is_ok))

    def __str__(self):
        sf = StringIO()
        self.dump(sf)
        rs = sf.getvalue()
        # turn into single line for this (yes, cheesy, but it kind of works out)
        fl = []
        for line in rs.split('\n'):
            fl.append(line.strip())
        ft = ' '.join(fl)
        return ft


class MatcherCleanHitResult(MatcherResult):
    """
    Used to represent a solid basic match.
    """
    def __init__(self, description, is_terminal=False):
        super(MatcherCleanHitResult, self).__init__(
            description, "representing a basic solid match",
            is_error=False, is_terminal=is_terminal)


class MatcherOverMatch(MatcherResult):
    """
    Used to represent too many matches for a given matcher. For example, expecting
    between 2 and 3 of something, and getting 4 of them.
    """
    def __init__(self, description, min, max, count, is_terminal=True):
        super(MatcherOverMatch, self).__init__(
            description, "representing too many matches for a given matcher",
            is_error=True, is_terminal=is_terminal)
        self.__base_description = description
        self.__count = count
        self.__max = max
        self.__min = min
        self.__update_description()

    def adjust_count(self, new_count):
        """
        Used to alter the overmatch with additional (over) matches, mostly
        for diagnostic purposes.
        """
        self.__count = new_count
        self.__update_description()

    def __update_description(self):
        new_descr = "{0} overmatched (count={1}, min={2}, max={3})".format(
            self.__base_description, self.__count, self.__min, self.__max)
        self._update_description(new_descr)


class MatcherOrderedMissMatch(MatcherResult):
    """
    Used to represent an error caused by misordered matches. For example,
    if the expectaion was to match from 1 to 2 of A and then 2 to 3 of B, but
    we saw 'ABA' or 'B'.
    """
    def __init__(self, description, min, max, matched_count):
        super(MatcherOrderedMissMatch, self).__init__(
            description,
            "representing misordered matches where A should follow B, but B was hit first",
            is_error=True, is_terminal=True)
        self.__base_description = description
        self.__matched_at_fail = matched_count
        self.__matched_after = 0
        self.__missed_after = 0
        self.__max = max
        self.__min = min
        self.__update_description()

    def bump_matched(self):
        """
        marks that a(nother) match happened after the matcher was missed. For example,
        if the expectation was 'AB', but we got 'BAA', The mismatch would get created
        for A (when its matcher 'missed' when seeing B). This method would get called
        twice for the two 'A's after that.
        """
        self.__matched_after += 1
        self.__update_description()

    def bump_missed(self):
        """
        marks that (another) miss happened. For example, if we were expected 'AB', but
        got 'BB', a mismwatch would be created for A (when its matcher 'missed' when the
        first 'B' was seen). Then this method would get called on the second 'B', since
        we would still be look for A.

        Note: I'm not 100% sure this is the right way to record this. These are, however,
        used only for reporting the failure to help do diagnostics.
        """
        self.__missed_after += 1
        self.__update_description()

    def __update_description(self):
        nd = "{0} out-of-order at {1} matched. Matches after {2}, Misses after {3}".format(
            self.__base_description, self.__matched_at_fail, self.__matched_after,
            self.__missed_after)
        self._update_description(nd)


class MatcherUnderMatch(MatcherResult):
    """
    Used to indicate we saw too few of something. For example, if we expected between
    2 and 5 of 'A', but only saw 1 of them.
    """
    def __init__(self, description, min, max, count):
        super(MatcherUnderMatch, self).__init__(
            description, "representing too few matches for a given matcher",
            is_error=True, is_terminal=False)
        self.__base_description = description
        self.__count = count
        self.__max = max
        self.__min = min
        self.__update_description()

    def __update_description(self):
        new_descr = "{0} undermatched (count={1}, min={2}, max={3})".format(
            self.__base_description, self.__count, self.__min, self.__max)
        self._update_description(new_descr)


class MatcherValidation(MatcherResult):
    """
    Used for payload validation error marking. These don't disqualify a match, but
    they do mean the match-set is in error. Currently only used in amqp-source,
    though this might migrate out of here completely.
    """
    def __init__(self, description, used_for):
        super(MatcherValidation, self).__init__(
            description, used_for, is_error=True, is_terminal=True)


class MatcherValidationMissmatch(MatcherValidation):
    def __init__(self, description, field_name, expected_value, found_value):
        d = "Field '{}' had value '{}' instead of expected value '{}' in {}".format(
            field_name, found_value, expected_value, description)
        super(MatcherValidationMissmatch, self).__init__(
            d, "representing a validation failure where a given field's value did not match the expected one")


class MatcherValidationMissingField(MatcherValidation):
    def __init__(self, description, field_name, expected_value):
        d = "Field '{}' was expected to have the value '{}' but did not exist in {}".format(
            field_name, expected_value, description)
        super(MatcherValidationMissingField, self).__init__(
            d, "representing a validation failure where a given field was expected but was not found")
