import sys
import os
from benchmark.manipulator import manipulator

# pylint: disable=no-name-in-module

if __name__ == '__main__':

    for arg in sys.argv[1:]:

        if arg.find('--getdir') == 0:
            print manipulator().get_data_path()
            run_test = False

        elif arg.find('--start') == 0:
            manipulator().start()
            run_test = False

        elif arg.find('--stop') == 0:
            manipulator().stop()
            run_test = False
