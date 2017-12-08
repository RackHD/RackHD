#!/bin/bash -x
# Copyright © 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

NETWORK="eth1"  #Host DHCP Server interface
PORT="5901" #Host port which is bind to container port

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit 1
fi

help()
{
    echo "setup-network.sh - setup network to run RackHD with Infrasim Nodes."
    echo "Usage: sudo ./setup-network.sh [options]"
    echo "Options:"
    echo "-i Specify a host interface to bind the container network"
    echo "-p The host port used to map the container's vnc port"
}

while getopts "hi:t:p:n:" args;do
    case ${args} in
        h)
            help
	        exit 0
            ;;
        i)
            NETWORK=$OPTARG
	        ;;
        p)
            PORT=$OPTARG
            ;;
        *)
            help
	        exit 1
	        ;;
    esac
done	

#create dummy network adapter rackhd to connect to the southbound network
modprobe dummy
ip link set name eth1 dev dummy0 up

# install and creaet an open-virtual switch to connect the nodes to 
which ovs-vsctl
if [ $? -ne 0 ]; then
    echo "Open vSwitch is not installed, please install and re-run the script, http://openvswitch.org"
    exti 1
fi

ovs-vsctl br-exists ovs-br0
if [ $? -ne 0 ]; then
    ovs-vsctl add-br ovs-br0
fi

PORTS=$(ovs-vsctl list-ports ovs-br0)
if [[ " ${PORTS[*]} " == *"$NETWORK"* ]]; then
    echo "$NETWORK is a port on ovs-br0"
else
    ovs-vsctl add-port ovs-br0 $NETWORK
fi

# Set IP addresso on ovs-br0 and bring up interface
ip addr add 172.31.128.1/24 dev ovs-br0
ip link set dev ovs-br0 up

