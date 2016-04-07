import sys
import getopt
from proboscis import register
from proboscis import TestProgram

def run_tests(api_ver, selected):

    if api_ver == '2':
        import benchmark.api_v2_0 as benchmark
    else:
        import benchmark.api_v1_1 as benchmark

    register(groups=['poller'], depends_on_groups=benchmark.benchmark_poller_tests)
    register(groups=['discovery'], depends_on_groups=benchmark.benchmark_discovery_tests)
    register(groups=['bootstrap'], depends_on_groups=benchmark.benchmark_bootstrap_tests)

    if selected == False:
        TestProgram(groups=['poller','discovery','bootstrap']).run_and_exit()
    else:
        TestProgram().run_and_exit()



if __name__ == '__main__':

    api_version = "1"
    group_selected = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["api_version=", "group="])
        for op, value in opts:
            if op == "--api_version":
                # Remove this arg from array to prevent TestProgram processing it
                sys.argv = filter(lambda x: x != op+'='+value, sys.argv)
                api_version = value
            if op == '--group':
                group_selected = True
            if op == "-h":
                print "Usage: benchmark.py [--api_version|--group]"
                exit()
    except getopt.GetoptError:
        sys.exit("option or arg is not supported")

    run_tests(api_version, group_selected)
