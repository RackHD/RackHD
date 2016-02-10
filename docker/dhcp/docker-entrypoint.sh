#!/bin/sh

# Copyright 2016, EMC, Inc.

# set -x

chown dhcp /var/lib/dhcp
# chmod 777 /var/lib/dhcp

touch /var/lib/dhcp/dhcpd.leases
chown dhcp /var/lib/dhcp/dhcpd.leases
# chmod 666 /var/lib/dhcp/dhcpd.leases

dhcpd -f -cf /etc/dhcp/dhcpd.conf -lf /var/lib/dhcp/dhcpd.leases --no-pid
