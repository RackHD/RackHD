#!/bin/bash

# This is a helper script to run the Redfish Service Validator on RackHD
# Only runs on Ubuntu 16, not compatible with 14
# Requires python3 and pip3 installed
# Usage:
# ./rackhd_redfish_service_validator.sh host:port

if [ -z $1 -o "$1" == "-h" ]; then
  echo "Usage: ./rackhd_redfish_service_validator.sh host:port"
  exit 1
fi

echo "**** Checking python3..."
python3 -V
if [ $? -gt 0 ]; then
  echo "python3 not installed"
  exit 1
fi

echo "**** Checking pip3..."
pip3 -V
if [ $? -gt 0 ]; then
  echo "pip3 not installed"
  exit 1
fi

echo "**** Checking  server..."
curl $1/api/2.0/config > /dev/null
if [ $? -gt 0 ]; then
  echo "Unable to contact server at $1"
  exit 1
fi

echo "**** Setting up virtual environment..."
rm -rf rsv1
virtualenv -p python3 rsv1

echo "**** Downloading RSV tool from GitHub..."
commitid=$(git ls-remote   https://github.com/DMTF/Redfish-Service-Validator.git HEAD |cut -f 1)
echo "Commit ID: $commitid"
rm -rf RSV-$commitid
git clone https://github.com/DMTF/Redfish-Service-Validator.git RSV-$commitid

echo "**** Downloading on-http from RackHD GitHub..."
rm -rf temp_rsv
git clone https://www.github.com/rackhd/on-http temp_rsv
mkdir RSV-$commitid/config
mkdir RSV-$commitid/SchemaFiles
mkdir RSV-$commitid/logs
cp -rp temp_rsv/static/DSP8010_2016.3/metadata RSV-$commitid/SchemaFiles

echo "**** Creating config file..."
echo \
"[Information]
Updated = May 8, 2017
Description = Redfish Service-Schema Conformance Tool 0.91
[SystemInformation]
TargetIP = $1 
SystemInfo = RackHD
UserName = admin
Password = admin123
[Options]
MetadataFilePath = ./SchemaFiles/metadata
LogPath = ./logs
SchemaSuffix = _v1.xml
Timeout = 30
UseSSL = False
CertificateCheck = Off
LocalOnlyMode = False
ServiceMode = Off
Session_UserName = admin
Session_Password = admin123" > RSV-$commitid/config/config.ini

echo "**** Executing Redfish validator..."
cd RSV-$commitid
pip3 install -r requirements.txt
python3 RedfishServiceValidator.py -c config/config.ini
exitcode=$?

echo ""
echo "**** Validator exited with status $exitcode"
echo "**** Validator Test Results located in RSV-$commitid/logs"
exit $exitcode

