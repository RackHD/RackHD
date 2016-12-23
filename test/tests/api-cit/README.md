Updates to convert a CIT script to FIT format.

Dependencies can use nosedep.
 - with nosedep, can setup dependencies and priorities within a file
 - can include as a plugin and if not needed, don't use dependencies in the test script
 - if dependecy fails, following tests in that file are skipped
 - single script dependencies only, so cannot depend on a test case outside the single test script

Current updates to a CIT script file, more will be coming:
  Placement:
  - updated scripts are currently being put into the directory api-cit

  Imports:
  - remove proboscis imports
  - include FIT common files
  - include unittest

  Intial Class definition:
  - change __init__(self) to setUp(self)
  - change class Name(object) to class Name(unittest.TestCase)

  UnitTest updates:
  - Comments using the format """ test info """ placed directly after def test_name(self) causes unittest to pick that up as the test name.
    To fix this for unittest, please change that comment to use # instead.  ie: # test info
    ie.  def test_one()
         ''' my first test '''
      Change to:
          def test_one()
          # my first test

  Probosics and nosedep:
  - comment out all "@test" proboscis specific groups
  - add @depends()  - for nosedep on def test_xxx.
    - If ordering is needed in the script, update the test names to be alphabetical.  (ie. test_01_xxxx, test_02_xxx)
      This is due to issue between unittest and nosedep during autodiscover. We are working on a fix. **
    - @depends(after=test_one), @depends(before=test_two)

  - Change of proboscis asserts to UnitTest assert format
    Most asserts will map easy:
        assert_not_equal = self.assertNotEqual
        assert_equal = self.assertEqual
        change parameter "message" to "msg"  - for assert call
         example:
           proboscis: assert_not_equal(0, len(obms), message='OBMs list was empty!')
           unittest:  self.assertNotEqual(0, len(obms), msg='OBMs list was empty!')

  - Dependency updates
    - An example, in the test scripts, some of the dependencies look for discovered nodes.  Instead of making a dependency on a specific test being run,
      we want to move the dependcies from a "test calling another test" to the "test calling a library/module" to verify what is needed.
      ie. if the node list needs to be present and populated, don't call the test "discover_nodes"
            instead call the nodes_list function in the library that will return a list of nodes you need (compute, switch)
      check if it is empty
      if not empty, verify obm settings are present if needed.
    - If you want to run a series of tests in a row, within a script, order them alphabetically and add the depends if the test should be skipped if the prior one failed.
    - Using unittest, you can run an 'individual' test, so having many dependencies tends to be cumbersome if you just need to verify a few things work.


