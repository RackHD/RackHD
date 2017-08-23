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
remove_old_box()
{
    OS_VER=ubuntu-14.04
    rm -rf  ~/VirtualBox\ VMs/rackhd-${OS_VER}
    OS_VER=ubuntu-16.04
    rm -rf  ~/VirtualBox\ VMs/rackhd-${OS_VER}
}

virtualBoxDestroyAll
remove_old_box
