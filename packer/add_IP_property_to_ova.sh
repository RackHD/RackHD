#!/bin/bash
set -e
###################################################
#Background:
#   for the purpose of RackHD deployment enviroment without DHCP on admin port (e.x.: eth0),
#   "OVF Environment" is leveraged to configure VM's IP during OVA/OVF deployment
#
#Implementation:
#   1. define customized fields in OVF template file(XML format)
#   2. when deploy RackHD OVA , you can specific the eth0 IP (thru OVF Env Parameter) like ```ovftool --prop:adminIP=1.2.3.4 .....```
#   3. in VM OS's bootup scripts: use VMWare Tool to retrieve IP and set the primary NIC(eth0 for example)
#
#  Reference: http://www.v-front.de/2014/01/building-self-configuring-nested-esxi.html
#
#Parameter:
#   the OVA file name to be converted.
###################################################################
if  [ ! -n "$1" ];  then
    echo "[Error] wrong usage of add_IP_property_to_ova.sh. the original ova file name should be given"
    exit -1
fi
OVA=$1
BASENAME=${OVA%.*}
OVF=$"${BASENAME}.ovf"

### validate the OVA
FILE_TYPE=`file ${OVA} | awk -F": " '{print $2}'`
if [ "${FILE_TYPE}" != "POSIX tar archive" ] ; then
    echo "[Error]:  ${OVA} is not a valid OVA file"
    exit -1
fi

rm -f $"${BASENAME}.mf" # remove checksum file, otherwise, existing mf file will prevent ovftool converting
echo "convert ${OVA} to OVF file, named ${OVF}"
ovftool $OVA  $OVF
if [ $? != 0 ]; then
    echo "[Error] ovftool exec failed..(ovftool $OVA  $OVF) exit"
    exit 1
fi

echo "modify the OVF adding property."

#######################################################
# Note : this is ESXi format. (other ESX version may varies )
# Add ProductSection/Property xml nodes under VirtualSystem xml node( kind of declare OVF Enviromental Properties)
#######################################################

################
#[ OVF Template Injection Step #1 ]
# Below 'sed' will "insert" below XML tree at the end of <VirtualSystem> tag of the OVF template file.
#     |-ProductSection
#     |----Info
#     |----Product
#     |----Category
#     |----Property #1
#     |----Property #..
#     |----Property #n
#################
sed -i 's/<\/VirtualSystem>/ \
  <ProductSection>    \
     <Info>Information about the installed software<\/Info> \
     <Product>Rackhd<\/Product> \
     <Category>adminnetwork<\/Category>  \
     <Property ovf:key="adminIP" ovf:type="string" ovf:userConfigurable="true"> \
        <Label>adminIP<\/Label> \
     <\/Property> \
     <Property ovf:key="adminGateway" ovf:type="string" ovf:userConfigurable="true"> \
        <Label>adminGateway<\/Label> \
     <\/Property> \
     <Property ovf:key="adminNetmask" ovf:type="string" ovf:userConfigurable="true"> \
        <Label>adminNetmask<\/Label> \
     <\/Property> \
     <Property ovf:key="adminDNS" ovf:type="string" ovf:userConfigurable="true"> \
        <Label>adminDNS<\/Label> \
     <\/Property>  \
  <\/ProductSection> \
<\/VirtualSystem>   \
/'  $OVF
################
#[ OVF Template Injection Step #2 ]
# specify the "OVF enviroment transport" method to VMWare Tools
###############
sed -i 's/<VirtualHardwareSection>/<VirtualHardwareSection ovf:transport="com.vmware.guestInfo" > /' $OVF



echo "reconvert back to OVA"
###############
#[ OVF Template Injection Step #3 ]
# update checksum
###############
NewChk=$(sha1sum $OVF | awk '{print $1}')
sed  -i -E  "s/SHA1\(.*ovf\)=.*$/SHA1\($OVF\)= $NewChk/g"  $"${BASENAME}.mf"
##############
#[ OVF Template Injection Step #4 ]
# re-package into OVA
##############
rm -f $OVA  #remove old OVA
ovftool $OVF $OVA
if [ $? != 0 ]; then
     echo "[Error] ovftool exec failed..(ovftool $OVF  $OVA) exit"
     exit 1
fi
echo "[Info] the new OVA is created , with customized ovf property feature : ${OVA}"
