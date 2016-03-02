#!/bin/sh

# Copyright 2016, EMC, Inc.

# set -x

cp -a -f /RackHD/downloads/* /RackHD/files/

while true; do
  date;
  sleep 120; # 2 minutes
  # sleep 21600; # 6 hours
done
