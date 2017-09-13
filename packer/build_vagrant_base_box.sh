#!/bin/bash -e

#########################################
#
#  Global variables
#
#########################################
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ANSIBLE_PLAYBOOK=rackhd_package
source $DIR/box_handler.sh
#########################################
#
#  Usage
#
#########################################
Usage(){
    echo "Function: this script is used to build ovf: the pre-build cache of vagrant box"
    echo "usage: $0 [arguments]"
    echo "    mandatory arguments:"
    echo "      --OS_VER: The version of the base os"
    echo "      --TARGET_DIR: The target directory to put ovf and log file"
}

#########################################
#
#  build ovf
#
#########################################
build(){
    pushd $DIR
    echo "[Info] Generate a parameter file pass to packer"
    CFG_FILE=template.cfg
    # parameter file pass to packer
    echo {                                                         > $CFG_FILE
    echo  \"playbook\": \"${ANSIBLE_PLAYBOOK}\",                   >> $CFG_FILE
    echo  \"vm_name\": \"rackhd-${OS_VER}\"                        >> $CFG_FILE
    echo }                                                         >> $CFG_FILE
    echo "[Info] the parameter file:"
    cat $CFG_FILE

    echo "[Info] Customize the template-${OS_VER}.json , to remove the vagrant-upload step"
    # pre-process the packer template file
    PACKER_TEMP=template-${OS_VER}.json.tmp
    TMP_FILE_STREAM=$(cat template-${OS_VER}.json)
    # Delete the post-processors blocks in the template.json, before sending to 'packer build'
    TMP_FILE_STREAM=$( jq 'del(.["post-processors"][0][1])' template-${OS_VER}.json | jq 'del(.["push"])')
    # Write back the template file
    echo "$TMP_FILE_STREAM" > $PACKER_TEMP
    echo "[Info] The template-${OS_VER}.json has been customized"

    $PACKER build --force --only=virtualbox-iso  --var-file=$CFG_FILE  ${PACKER_TEMP} | tee packer-install.log && \
    ## Check packer build command status
    ## Because above we use pipeline, so use  ${PIPESTATUS[0]} to catch return-code of command before pipeline.(only works on bash)
    if [ ${PIPESTATUS[0]} != 0 ]; then
        echo "[ERROR] Packer Build failed.. exit"
        exit 3
    fi
    # src dir may be the same with TARGET_DIR
    set +e
    mv  output-*/*.* $TARGET_DIR/
    mv packer-install.log $TARGET_DIR
    set -e
    popd
}


###################################################################
#
#  Parse and check Arguments
#
##################################################################
parseArguments(){
    while [ "$1" != "" ]; do
        case $1 in
            --OS_VER )                      shift
                                            OS_VER=$1
                                            ;;
            --TARGET_DIR )                  shift
                                            TARGET_DIR=$1
                                            ;;
            * )                             Usage
                                            exit 1
        esac
        shift
    done
    if [ ! -n "${OS_VER}" ] ; then
        echo "[ERROR]Arguments OS_VER is required!"
        Usage
        exit 1
    fi

    if [ ! -n "${TARGET_DIR}" ]; then
        echo "[ERROR]Arguments TARGET_DIR is required"
        Usage
        exit 1
    fi
    mkdir -p ${TARGET_DIR}
}

########################################################
#
# Main
#
######################################################
main(){
    parseArguments "$@"
    checkDependencies
    preparePackerEnv
    cleanUpBox
    trap cleanUpBox SIGINT SIGTERM SIGKILL EXIT
    build
}

main "$@"
