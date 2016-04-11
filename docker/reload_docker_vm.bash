#!/bin/bash

# Copyright 2016, EMC, Inc.

# Reload boot2docker.iso VM using Vagrant

# export B2D_NFS_SYNC=1
export B2D_DISABLE_PRIVATE_NETWORK=1
vagrant reload b2d
