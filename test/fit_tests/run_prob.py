

#
# Note, this is a temporary script to run self-tests
# on the infralogging stuff. This will be removed
# as the group-support is added to allow test-self-tests
# to the main runner.

def run_tests():
    from proboscis import TestProgram
    from common.logging import test_infra_logging

    # Run and exit
    TestProgram().run_and_exit()

if __name__ == "__main__":
    run_tests()
