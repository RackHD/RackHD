#!/bin/bash

#Copyright © 2017 Dell Inc. or its subsidiaries.  All Rights Reserved. 

INTERFACE=eth0
BRIDGE=br0

ifconfig $INTERFACE 0.0.0.0
ifconfig $INTERFACE promisc
brctl addbr $BRIDGE 
brctl addif $BRIDGE $INTERFACE
brctl setfd $BRIDGE 0
brctl sethello $BRIDGE 1
brctl stp $BRIDGE no
mv /sbin/dhclient /usr/sbin/dhclient
/usr/sbin/dhclient $BRIDGE
ifconfig
infrasim node start

tail -f /var/log/infrasim/default/*.log
