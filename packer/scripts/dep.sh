#!/bin/bash
#
# Setup the the box. This runs as root
apt-get -y update

# to support using the ansible provisioner
apt-get -y install expect aptitude python-dev python-pip python-yaml libffi-dev
pip install --upgrade setuptools
pip install ansible==2.2.0.0

# set a friendly hostname
# by default, the hostname in both /etc/hosts & /etc/hostname are obtained from DHCP server during install.
rm -f /etc/hostname
echo "rackhd" > /etc/hostname
#Below two lines were moved from scripts/cleanup.sh. I can't recall why they didn't go with /etc/hostname change together...
NEW_HOST_NAME=$(cat /etc/hostname)
sed -i  "/127.0.1.1/,/$/c127.0.1.1\t${NEW_HOST_NAME}" /etc/hosts
