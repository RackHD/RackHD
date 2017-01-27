#!/bin/bash

# Run code checks (pylint for example)
#
# Command forms:
#   mkcheck.sh
#       Runs checker and writes to stdout
#
#   mkcheck.sh <pkg_version> <pkg_format>
#       Runs checker and writes to file named
#           onserve_<pkg_version>_pylint.<pkg_format>
#
#       <pkg_format> can be 'html', 'text'.  See pylint
#           for more.
#

if [ $# -eq 0 ]; then
    format="text"
    pylint_output_file="/dev/stdout"
    copyright_output_file="/dev/stdout"
elif [ $# -eq 1 ]; then
    format="text"
    pylint_output_file="/dev/stdout"
    copyright_output_file="/dev/stdout"
elif [ $# -eq 2 ]; then
    PKG_VERSION=$1
    format=$2
    pylint_output_file="onserve_${PKG_VERSION}_pylint.${format}"
    copyright_output_file="onserve_${PKG_VERSION}_copyright.${format}"
else
    echo "bad command form"
    echo "mkcheck.sh [<pkg_version> <pkg_format>]"
    exit 1
fi

final_status=0

scandirs=`find * -prune -type d`

errors_only="-E"

pylint ${errors_only} --rcfile=pylintrc --output-format=${format} ${scandirs} > ${pylint_output_file}
status=$?

if [ ${status} -ne 0 ]; then
    echo "Pylint errors:"
    if [ "${pylint_output_file}" != "/dev/stdout" ]; then
        cat ${pylint_output_file}
    fi
    echo ""
    echo "Python checker failed.  Clean up code and retry"
    final_status=$status
else
    echo "Python checker succeeded"
fi

# No copyright checking yet
#./checkCopyright.sh > ${copyright_output_file}
#status=$?
#if [ ${status} -ne 0 ]; then
#    if [ "${copyright_output_file}" != "/dev/stdout" ]; then
#        cat ${copyright_output_file}
#    fi
#    echo "Copyright checker failed.  Add copyrights and retry"
#    final_status=$status
#else
#    echo "Copyright checker succeeded"
#fi

exit ${final_status}
