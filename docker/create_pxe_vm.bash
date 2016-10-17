#!/bin/bash

# Copyright 2016, EMC, Inc.

# Create PXE VM for VirtualBox

set -e # fail on error
set -x # debug commands

if [[ ! -e $NAME.vdi ]]; then # check to see if PXE vm already exists
    echo "Creating PXE VM: $NAME"
    VBoxManage createvm --name $NAME --register;
    VBoxManage createhd --filename $NAME --size 8192;
    VBoxManage storagectl $NAME --name "SATA Controller" --add sata --controller IntelAHCI
    VBoxManage storageattach $NAME --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium $NAME.vdi
    VBoxManage modifyvm $NAME --ostype Ubuntu --boot1 net --memory 768;
    VBoxManage modifyvm $NAME --nic1 intnet --intnet1 closednet --nicpromisc1 allow-all;
    VBoxManage modifyvm $NAME --nictype1 82540EM --macaddress1 auto;
fi
