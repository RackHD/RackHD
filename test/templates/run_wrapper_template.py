'''
Copyright 2016, EMC, Inc.

Author(s):

FIT test wrapper script template
'''

import fit_path  # NOQA: unused import
import unittest

from common import fit_common


class wrapper_template(unittest.TestCase):

    def test01(self):
        self.assertEqual(fit_common.run_nose(fit_common.TEST_PATH + '/tests/templates/fit_test_template.py'),
                         0, 'template test failed as expected.')


if __name__ == '__main__':
    unittest.main()
