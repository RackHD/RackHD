#!/bin/bash
set -e

##########################################################
# retrieve NIC name via ```ip addr``` command, by given id
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
    tmp=$( ip addr|grep "^${1}:" | awk '{print $2}')
    if [[ "$tmp" == "" ]];
    then
        echo "[Error]: Invalid Parameter passed to get_nic_name_by_index(): NIC ID=$1";
        exit 1
    fi
    name=${tmp/:/}  # remove the ":"
    echo $name
}

#################################
# retrieve secondary NIC Name(control port of RackHD)
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


########################################
# Main
#######################################
Control_NIC=$(get_secondary_nic_name)

# Update the /etc/default/isc-dhcp-server, let DHCP Service running on Control Port.
line="INTERFACES=\"$Control_NIC\""
echo $line >> /etc/default/isc-dhcp-server

echo "[Info] The Control NIC is ${Control_NIC}. Added it into /etc/default/isc-dhcp-server"
