"""
Copyright 2016, EMC, Inc.
"""
import plugin_test_helper

class TestSMPSingleOkSequence(plugin_test_helper.resolve_helper_class()):
    suitepath = plugin_test_helper.resolve_suitepath('stream-base', 'one_pass')

    def verify(self):
        self._check_sequence_pre_test()
        self._check_sequence_test('test_one_pass.test_one')
        self._check_sequence_post_test()

class TestSMPDoubleOkSequence(plugin_test_helper.resolve_helper_class()):
    suitepath = plugin_test_helper.resolve_suitepath('stream-base', 'two_pass')

    def verify(self):
        self._check_sequence_pre_test()
        self._check_sequence_test('test_two_pass.test_one_of_two_pass')
        self._check_sequence_test('test_two_pass.test_two_of_two_pass')
        self._check_sequence_post_test()
