#!/bin/bash

# Copyright 2016, EMC, Inc.

# Create boot2docker.iso VM using Vagrant

# export B2D_NFS_SYNC=1
export B2D_DISABLE_PRIVATE_NETWORK=1
vagrant up b2d
