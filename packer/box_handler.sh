#!/bin/bash +e

# To resolve error message as below, which is a dirty worksspace
# Build 'virtualbox-ovf' errored: Error enabling VRDP: VBoxManage error: VBoxManage: error: The machine 'rackhd-ubuntu-14.04' is already locked for a session (or being unlocked)
virtualBoxDestroyAll() {
    set +e
    for uuid in `vboxmanage list vms | awk '{print $2}' | tr -d '{}'`; do
        echo "shutting down vm ${uuid}"
        vboxmanage controlvm ${uuid} poweroff
        echo "deleting vm ${uuid}"
        vboxmanage unregistervm ${uuid}
    done
    pkill packer
    set -e
}

# To resolve issue during packer build:
# Machine settings file '/home/jenkins/VirtualBox VMs/rackhd-ubuntu-14.04/rackhd-ubuntu-14.04.vbox' already exists
removeOldBox()
{
    local OS_VER=ubuntu-14.04
    rm -rf  ~/VirtualBox\ VMs/rackhd-${OS_VER}
    OS_VER=ubuntu-16.04
    rm -rf  ~/VirtualBox\ VMs/rackhd-${OS_VER}
}

#########################################
#
# Clean up box
#
#########################################
cleanUpBox(){
    virtualBoxDestroyAll
    removeOldBox
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
    if [ -z "$(which jq)" ] ; then
        echo "${ERROR_HEADER} jq is not installed . please install it, e.x. sudo apt-get install jq... Aborting. "
        exit 5
    fi
    set -e
}

#########################################
#
#  prepare environment for packer
#
#########################################
preparePackerEnv(){
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
    echo "[Info] Show current environment"
    vagrant -v
    $PACKER -v  # $? of "packer -v" is 1 ...
    set -e
}

