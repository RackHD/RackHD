import sys
import os
import getopt
from proboscis import register
from proboscis import TestProgram

def run_tests(api_ver, selected):

    if api_ver == '2':
        import benchmark.api_v2_0 as benchmark
    else:
        import benchmark.api_v1_1_tests

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

        benchmark.ansible_ctl.dispose()
    else:
        TestProgram().run_and_exit()



if __name__ == '__main__':

    api_version = "1"
    group_selected = False

    for arg in sys.argv[1:]:
        if arg[:14] == '--api_version=':
            # Remove this arg from array to prevent TestProgram processing it
            api_version = arg[14]
            sys.argv.remove(arg)
        elif arg[:8] == '--group=':
            group_selected = True

    run_tests(api_version, group_selected)
