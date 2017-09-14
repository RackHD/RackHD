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
#  build box
#
#########################################
build(){
    pushd $DIR
    echo "[Info] Generate a parameter file pass to packer"
    CFG_FILE=template.cfg
    # parameter file pass to packer
    echo {                                                         > $CFG_FILE
    echo  \"playbook\": \"${ANSIBLE_PLAYBOOK}\",                   >> $CFG_FILE
    echo  \"vm_name\": \"rackhd-${OS_VER}\",                       >> $CFG_FILE
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
        mkdir -p output-virtualbox-iso
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
    preparePackerEnv
    cleanUpBox
    trap cleanUpBox SIGINT SIGTERM SIGKILL EXIT
    build
}

main "$@"

