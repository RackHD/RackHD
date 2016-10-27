#!/bin/bash
echo -e "\nauto eth1\niface eth1 inet static\n   address 172.31.128.1\n   netmask 255.255.252.0" >> /etc/network/interfaces