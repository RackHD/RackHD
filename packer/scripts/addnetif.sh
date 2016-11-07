#!/bin/bash

#######################################
setIP(){

    SECONDARY_NIC=$1
    IP=172.31.128.1
    MASK=255.255.252.0

    echo -e "\nauto $SECONDARY_NIC\niface $SECONDARY_NIC inet static\n   address $IP\n   netmask $MASK" >> /etc/network/interfaces
}


########################################
# Set Secondary NIC IP to 172.31.128.1
#######################################
Ubuntu_VER=$(lsb_release -a | grep "Release:"| awk '{print $2}')

if [[ $(echo $Ubuntu_VER | grep "14.04") != "" ]]
then
    setIP eth1
fi

if [[ $(echo $Ubuntu_VER | grep "16.04") != "" ]]
then
    # 16.04, using vmxnet3 NIC dev , the NIC name will be ens 160, 192, 224, 256
    #        using e1000   NIC dev , the NIC name will be ens 32, 33, 34, 35
    if [[ $( ip addr|grep ens33 ) != "" ]]
    then
        setIP ens33
    fi

    if [[ $( ip addr|grep ens192 ) != "" ]]
    then
        setIP ens192
    fi
fi
