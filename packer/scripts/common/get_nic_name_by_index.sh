#!/bin/bash

##########################################################
# retrieve NIC name via ```ip addr``` command, by given id
#
# Param: Index of NIC(starting from 1)
#
# echo:  the NIC Name
#
# Exception:  exit non-zero with echo error message
##########################################################
get_nic_name_by_index()
{
    #######################
    # This script is to obtain and echo the NIC name (lo/eth0/eth1) by index(1/2/3) shown in ```ip addr```
    #
    #
    # ip addr will show:
    #
    #1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default
    #.......
    #2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 ...
    #.......
    #3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pf....
    #......
    #
    ########################
    ID=$1
    if ! [[ "$ID" =~ ^[0-9]+$ ]] || [[ "$ID" -eq 0 ]]; then
        echo "[Error]: Invalid Parameter passed to get_nic_name_by_index(): NIC ID=${ID} should be number and be larger than 0.";
        exit 1
    fi

    tmp=$( ip addr|grep "^${ID}:" | awk '{print $2}')

    # the output should be like "lo:", "eth1:", "br-123asdf23:" if this nic index exists
    if [[ "$tmp" == "" ]] || ! [[ $(echo $tmp|grep ":$") ]]
    then
        echo "[Error]: Invalid Parameter passed to get_nic_name_by_index(): NIC ID=${ID} not detected";
        exit 2
    fi
    name=${tmp/:/}  # remove the ":"
    echo $name
}

#################################
# retrieve secondary NIC Name(example :control port of RackHD), skipping the loopback dev(lo)
#
# echo:  the NIC Name
################################
get_secondary_nic_name()
{

    # By Default, the Control Port index is 3. say: eth1/enp0s8/ens33...
    Sec_NIC_Index=3;


    # if the index 1 is not loopback device, then eth0 may starts from index 1.
    NIC1=$(get_nic_name_by_index 1)
    if [[ $NIC1 != "lo" ]]; then
        Sec_NIC_Index=$(expr $Sec_NIC_Index - 1 )
    fi

    Sec_NIC=$(get_nic_name_by_index $Sec_NIC_Index)

    echo $Sec_NIC
}
