import sys
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

    if selected == False:
        TestProgram(groups=['poller','discovery','bootstrap']).run_and_exit()
    else:
        TestProgram().run_and_exit()



if __name__ == '__main__':

    api_version = "1"
    group_selected = False

    for arg in sys.argv[1:]:
        if arg[:14] == '--api_version=':
            # Remove this arg from array to prevent TestProgram processing it
            sys.argv = filter(lambda x: x != op+'='+value, sys.argv)
            api_version = value
        elif arg[:8] == '--group=':
            group_selected = True

    run_tests(api_version, group_selected)
