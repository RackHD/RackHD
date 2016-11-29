#!/bin/bash
#
# Setup the the box. This runs as root
apt-get -y update

# to support using the ansible provisioner
apt-get -y install ansible

# set a friendly hostname
rm -f /etc/hostname
echo "rackhd" > /etc/hostname
