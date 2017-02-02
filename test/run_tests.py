#!/usr/bin/env python

'''
Copyright 2016, EMC, Inc

Author(s):
George Paulos
'''

# set path to common libraries
import sys
import subprocess

sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# validate command line args
fit_common.mkargs()

# Run tests
EXITCODE = fit_common.run_nose()
exit(EXITCODE)

