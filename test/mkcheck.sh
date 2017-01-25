#!/bin/bash

# Copyright 2017, EMC, Inc.

# Run code checks (pylint for example)
#
# Command forms:
#   mkcheck.sh
#       Runs checker and writes to to local file
#   mkcheck.sh <pkg_format>
#       <pkg-formmat> can be either "text" or "html"
#       with "text" being the default if no option
#       specified.
#
#   output file:
#        rackhd_test_pylint.<pkg_format>
#

format="text"
if [ $# -eq 1 ]; then
    format="$1"
fi

if [[ "${format}" != "text" && "${format}" != "html" ]]; then
    echo "bad command form"
    echo "mkcheck.sh <[text|html]>"
    exit 1
fi

pylint_output_file=rackhd_test_pylint.${format}
status=0

scandirs="*.py common modules stream-monitor util tests templates deploy config benchmark"
errors_only="-E"
pylint ${errors_only} --rcfile=pylintrc --output-format=${format} . ${scandirs} > ${pylint_output_file}
if [ $? -ne 0 ]; then
    if [ "${format}" == "text" ]; then
        cat ${pylint_output_file}
    fi
    echo "Python checker failed.  Clean up code and retry"
    status=1
else
    echo "Python checker succeeded"
fi

exit ${status}
