#!/bin/bash -e

############################################
# Global variable
############################################
RACKHD_TEST_DIR="$( cd -P "$( dirname "$0" )" && pwd )"

#############################################
#
# Usage
############################################
Usage(){
    set +x
    echo "Function: This script is used to set up environment for FIT and run FIT."
    echo "Usage: $0 [OPTIONS]"
    echo "  OPTIONS:"
    echo "    Mandatory options:"
    echo "    Optional options:"
    echo "      -g, --TEST_GROUP: test group of FIT, such as imageservice, smoke"
    echo "      -s, --TEST_STACK: target test stack of FIT, such as docker, vagrant..."
    echo "      -v, --TEST_LOG_LEVEL: log level of FIT, 0 is the least verbose for log output , 9 is full on logging including info/debug etc. A good mix of console/file output is at level 4 or 5."
    echo "      -w, --WORKSPACE: The directory of workspace( where the test report will be )"
    echo "      -e, --TEST_EXTRA_OPTIONS: The extra options of FIT, such as '-extra myconfig.json -config my-dir -nodeid abcd'"
    set -x
}


#############################################
#
#  Create the virtual env for FIT  
#
############################################
setupVirtualEnv(){
    pushd ${RACKHD_TEST_DIR}
    virtual_env_name=FIT
    rm -rf .venv/$virtual_env_name
    ./mkenv.sh $virtual_env_name
    source myenv_$virtual_env_name
    popd
}

deactivateVirtualEnv(){
    deactivate
}

####################################
#
# Collect the test report
#
##################################
collectTestReport()
{
    if [ -n "$WORKSPACE" ]; then
        mkdir -p ${WORKSPACE}/xunit-reports
        mv ${RACKHD_TEST_DIR}/*.xml ${WORKSPACE}/xunit-reports
        echo "Test reports are xml files, under here: ${WORKSPACE}/xunit-reports"
    else
        echo "Test reports are xml files, under here: ${RACKHD_TEST_DIR}"
    fi
}


####################################
#
# Start to run FIT tests
#
##################################
runFIT() {
    set +e
    netstat -ntlp
    pushd ${RACKHD_TEST_DIR}
    echo "########### Run FIT Smoke Test #############"
    echo "python run_tests.py ${TEST_GROUP} -stack ${TEST_STACK} -v ${TEST_LOG_LEVEL} ${TEST_EXTRA_OPTIONS} -xunit"
    python run_tests.py ${TEST_GROUP} -stack ${TEST_STACK} -v ${TEST_LOG_LEVEL} ${TEST_EXTRA_OPTIONS} -xunit
    if [ $? -ne 0 ]; then
        echo "Failed to run FIT"
        collectTestReport
        exit 1
    fi
    collectTestReport
    popd
    set -e
}


##############################################
#
# Set up test environment and run test
#
#############################################
runTests(){
    setupVirtualEnv
    runFIT
}

##############################################
#
# Back up exist dir or file
#
#############################################
backupFile(){
    if [ -d $1 ];then
        mv $1 $1-bk
    fi
    if [ -f $1 ];then
        mv $1 $1.bk
    fi
}

#######################################
#
# Main
#
#####################################
main(){
    while [ "$1" != "" ]; do
        case $1 in
            -w | --WORKSPACE )              shift
                                            WORKSPACE=$1
                                            ;;
            -g | --TEST_GROUPS )            shift
                                            TEST_GROUP="$1"
                                            ;;
            -s | --TEST_STACK )             shift
                                            TEST_STACK="$1"
                                            ;;
            -v | --TEST_LOG_LEVEL )         shift
                                            TEST_LOG_LEVEL="$1"
                                            ;;
            -e | --TEST_EXTRA_OPTIONS )     shift
                                            TEST_EXTRA_OPTIONS="$1"
                                            ;;
            * )                             echo "[Error]$0: Unkown Argument: $1"
                                            Usage
                                            exit 1
        esac
        shift
    done

    if [ ! -n "$TEST_GROUP" ]; then
        TEST_GROUP="-test tests -group smoke"
    fi

    if [ ! -n "$TEST_STACK" ]; then
        TEST_STACK="docker_local_run"
    fi

    if [ ! -n "$TEST_LOG_LEVEL" ]; then
        TEST_LOG_LEVEL="4"
    fi
    trap deactivateVirtualEnv SIGINT SIGTERM SIGKILL EXIT   
    runTests
}

main "$@"
