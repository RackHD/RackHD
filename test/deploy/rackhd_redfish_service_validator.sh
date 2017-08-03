#!/bin/bash

# This is a helper script to run the Redfish Service Validator on RackHD
# Usage:
# ./rackhd_redfish_service_validator.sh host:port

if [ -z $1 ]; then
  echo "Usage: ./rackhd_redfish_service_validator.sh host:port"
  exit
fi

# set up virtual environment
rm -rf rsv1
echo \
"beautifulsoup4==4.5.3
requests" > rsv_requirements.txt
virtualenv -p python3 rsv1
source rsv1/bin/activate
pip3 install -r rsv_requirements.txt

# download RSV
rm -rf RSV
git clone https://github.com/DMTF/Redfish-Service-Validator.git RSV

# download on-http
rm -rf temp_rsv
git clone https://www.github.com/rackhd/on-http temp_rsv
mkdir RSV/config
mkdir RSV/SchemaFiles
mkdir RSV/logs
cp -rp temp_rsv/static/DSP8010_2016.3/metadata RSV/SchemaFiles

# create config file
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
Session_Password = admin123" > RSV/config/config.ini

# execute validator
cd RSV
python3 RedfishServiceValidator.py -c config/config.ini

echo ""
echo "Validator Test Results located in RSV/logs"
exit

