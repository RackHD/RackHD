#!/bin/bash
#
# Setup the the box. This runs as root
apt-get -y update

# to support using the ansible provisioner
apt-get -y install ansible

# enable sudo local access to anyone logging in (for ansible)
#echo '%sudo    ALL=(ALL)  NOPASSWD:ALL' >> /etc/sudoers

# You can install anything you need here.
