#!/bin/bash

set -e

#Load library func, it was loaded by packer to /tmp/ in previous steps
source /tmp/get_nic_name_by_index.sh

#######################################
# Force set Secondary NIC static IP
######################################
setIP(){

    SECONDARY_NIC=$1
    IP=172.31.128.1
    MASK=255.255.252.0

    echo -e "\nauto $SECONDARY_NIC\niface $SECONDARY_NIC inet static\n   address $IP\n   netmask $MASK" >> /etc/network/interfaces
}


########################################
# Set Secondary NIC IP to 172.31.128.1
#######################################
Control_NIC=$(get_secondary_nic_name) 
echo "Setting static IP 172.31.128.1 for ${Control_NIC}"
setIP ${Control_NIC}


