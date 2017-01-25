import sys
import os
from benchmark.manipulator import manipulator
from proboscis import register
from proboscis import TestProgram

# pylint: disable=no-name-in-module

def run_tests(api_ver, selected):

    if api_ver == '2':
        # No actual case yet
        import benchmark.tests.api_v2_0_tests
    else:
        import benchmark.tests.api_v1_1_tests

    register(groups=['poller'], depends_on_groups=['benchmark.poller'])
    register(groups=['discovery'], depends_on_groups=['benchmark.discovery'])
    register(groups=['bootstrap'], depends_on_groups=['benchmark.bootstrap'])

    if selected == False:
        # Three test groups need to run sequentially,
        # while proboscis schedules tests in different group at a mixed manner.
        # Adding dependencies among groups is not prefered since they also can be executed separately.
        # So TestProgram needs to be called three times for different groups.
        # TestProgram calls sys.exit() when finishing, thus subprocess is created for each group.
        for case in ['poller', 'discovery', 'bootstrap']:
            child_pid = os.fork()
            if (child_pid == 0):
                TestProgram(groups=[case]).run_and_exit()
            pid, status = os.waitpid(child_pid, 0)
            if (status != 0):
                break;

    else:
        TestProgram().run_and_exit()

    # pylint: disable=no-member
    benchmark.tests.ansible_ctl.dispose()


if __name__ == '__main__':

    api_version = "1"
    group_selected = False
    run_test = True

    # We don't use getopt here since there is no need enumerate all parameters for proboscis,
    # just process some additional ones is enough
    for arg in sys.argv[1:]:

        if arg.find('--api_version=') == 0:
            # Remove this arg from array to prevent TestProgram processing it
            api_version = arg[14]
            sys.argv.remove(arg)

        elif arg.find('--group=') == 0:
            group_selected = True

        elif arg.find('--getdir') == 0:
            print manipulator().get_data_path()
            run_test = False

        elif arg.find('--start') == 0:
            manipulator().start()
            run_test = False

        elif arg.find('--stop') == 0:
            manipulator().stop()
            run_test = False

    if run_test:
        run_tests(api_version, group_selected)
