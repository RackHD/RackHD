#!/bin/bash -e

#########################################
#
#  Global variables
#
#########################################
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ANSIBLE_PLAYBOOK=rackhd_package
#########################################
#
#  Usage
#
#########################################
Usage(){
    echo "Function: this script is used to build vagrant box"
    echo "usage: $0 [arguments]"
    echo "    mandatory arguments:"
    echo "      --OS_VER: The version of the base os"
    echo "      --RACKHD_VERSION: The version of rackhd debian package"
    echo "      --DEBIAN_REPOSITORY: The apt repository of rackhd debian package, such as: deb https://dl.bintray.com/rackhd/debian trusty release"
    echo "      --TARGET_DIR: The target directory to put box and log file"
    echo "    Optional Arguments:"
    echo "      --CACHE_IMAGE_DIR: The directory of cache images(ovf, vmdk)"
}

#########################################
#
#  check dependencies
#
#########################################
checkDependencies(){
    set +e
    echo "[Info] Start to check the dependencies"
    packer_path=$( which packer )
    if [ -z "$packer_path" ];then
        echo "[ERROR] packer is not installed . please install it."
        exit 5
    fi
    vagrant_path=$( which vagrant )
    if [ -z "$vagrant_path" ];then
        echo "[ERROR] vagrant is not installed . please install it."
        exit 5
    fi
    jq_path=$(which jq)
    if [ ! -n "$(which jq)" ] ; then
        echo "${ERROR_HEADER} jq is not installed . please install it, e.x. sudo apt-get install jq... Aborting. "
        exit 5
    fi
    set -e
}

#########################################
#
#  prepare environment
#
#########################################
prepareEnv(){
    set +e
    echo "[Info] Prepare environment"
    PACKER=packer
    if [ -x /opt/packer/packer ];then
        PACKER=/opt/packer/packer
    fi
    PACKER_CACHE_DIR=$HOME/.packer_cache
    # Enable Verbose Packer Logging
    # see https://www.packer.io/docs/other/environmental-variables.html for details
    export PACKER_LOG=1
    export PACKER_LOG_PATH=./packer-debug.log
    export PACKER_NO_COLOR=1  # for Jenkins usage. if manual run, suggest to turn color on (set to 0)
    pkill $PACKER
    bash $DIR/cleanup_vbox.sh
    echo "[Info] Show current environment"
    vagrant -v
    $PACKER -v  # $? of "packer -v" is 1 ...
    set -e
}

build(){
    pushd $DIR
    echo "[Info] Generate a parameter file pass to packer"
    CFG_FILE=template.cfg
    # parameter file pass to packer
    echo {                                                         > $CFG_FILE
    echo  \"playbook\": \"${ANSIBLE_PLAYBOOK}\",                   >> $CFG_FILE
    echo  \"rackhd_version\": \"${RACKHD_VERSION}\",               >> $CFG_FILE
    echo  \"deb_repository\": \"${DEBIAN_REPOSITORY}\"             >> $CFG_FILE
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

    if [ -n "$CACHE_IMAGE_DIR" ];then
        mkdir output-virtualbox-iso
        cp $CACHE_IMAGE_DIR/* output-virtualbox-iso
        #Build from cache template, and output the final image .(ovf-->box)
        $PACKER build --force --only=virtualbox-ovf  --var-file=$CFG_FILE --var "playbook=${ANSIBLE_PLAYBOOK}_mini" ${PACKER_TEMP} | tee packer-install.log
    else
        #Build from scratch, virtualbox: iso-->ovf-->box
        $PACKER build --force --only=virtualbox-iso  --var-file=$CFG_FILE  ${PACKER_TEMP} | tee packer-install.log && \
        $PACKER build --force --only=virtualbox-ovf  --var-file=$CFG_FILE  --var "playbook=${ANSIBLE_PLAYBOOK}_mini" ${PACKER_TEMP} | tee packer-install.log
    fi
    ## Check packer build command status
    ## Because above we use pipeline, so use  ${PIPESTATUS[0]} to catch return-code of command before pipeline.(only works on bash)
    if [ ${PIPESTATUS[0]} != 0 ]; then
        echo "[ERROR] Packer Build failed.. exit"
        exit 3
    fi

    mv packer_virtualbox-ovf_virtualbox.box $TARGET_DIR/rackhd-${OS_VER}-${RACKHD_VERSION}.box
    mv packer-install.log $TARGET_DIR
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
            --RACKHD_VERSION )              shift
                                            RACKHD_VERSION=$1
                                            ;;
            --DEBIAN_REPOSITORY )       shift
                                            DEBIAN_REPOSITORY=$1
                                            ;;
            --CACHE_IMAGE_DIR )             shift
                                            CACHE_IMAGE_DIR=$1
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

    if [ ! -n "${RACKHD_VERSION}" ]; then
        echo "[ERROR]Arguments RACKHD_VERSION is required"
        Usage
        exit 1
    fi

    if [ ! -n "${DEBIAN_REPOSITORY}" ]; then
        echo "[ERROR]Arguments DEBIAN_REPOSITORY is required"
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
    prepareEnv
    build
}

main "$@"

