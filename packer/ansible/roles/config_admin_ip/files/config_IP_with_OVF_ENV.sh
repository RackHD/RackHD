#!/bin/bash -e
###################################################
# Summary:
#   1. use VMWare Tool(vmtoolsd) to retrieve OVF ENV Parameters
#   2. parse the XML format( via getprops_from_ovfxml()) and retrieve the network settings
#   3. modify the /etc/network/interfaces
#   4. ifdown the primary NIC , then ifup (to let /etc/network/interfaces takes effect)
#
# Reference: http://www.v-front.de/2014/01/building-self-configuring-nested-esxi.html
# Note: for different ESXi version, the OVF XML Propertity format varies.
# Note: this feature is only supported by vCenter( not supported by vSphere)
####################################################


getprops_from_ovfxml() {
python - <<EOS
from xml.dom.minidom import parseString
ovfEnv = open("$1", "r").read()
dom = parseString(ovfEnv)
section = dom.getElementsByTagName("PropertySection")[0]
for property in section.getElementsByTagName("Property"):
   key = property.getAttribute("oe:key").replace('.','_')
   value = property.getAttribute("oe:value")
   print "{0}={1}".format(key,value)
dom.unlink()
EOS
}

#####################################################

vmtoolsd --cmd='info-get guestinfo.ovfEnv' >/tmp/ovf.xml
arr=$(getprops_from_ovfxml /tmp/ovf.xml)


### Note : the KEY here should align with the OVF Template Injection Properities' Label
IP_KEY="adminIP="
DNS_KEY="adminDNS="
GW_KEY="adminGateway="
MASK_KEY="adminNetmask="

if [[ ${#arr[@]} -eq 0  ]]
then
    echo "[Info]: Skip IP auto Config for Vagrant Box or unconfigured Vmware VM."
    echo "[Info]: OVF ENV did not be detected. either VMWare Tools not working or OVA not properily setting. "
    exit 0
fi

for line in ${arr[@]}
do
        echo $line
done


PRI_ETH=eth0
SEC_ETH=eth1
##########################################
## Detect Ubuntu Version and Primary NIC Naming
##
##
## This script is based an asumption that : the secondary NIC exists and NICs follow below convention:
## eth0 ,  eth1,   eth2
## ens32,  ens33,  ens34
## ens160, ens192, ens224
##########################################
if [[ $( ip addr|grep eth0 ) != "" ]]
then
     PRI_ETH=eth0
     SEC_ETH=eth1
fi
if [[ $( ip addr|grep ens32 ) != "" ]]
then
     PRI_ETH=ens32
     SEC_ETH=ens33
fi
if [[ $( ip addr|grep ens160 ) != "" ]]
then
     PRI_ETH=ens160
     SEC_ETH=ens192
fi




## The initialized primary eth setting
PRIM_ETH_CFG="#The primary network interface\n
auto ${PRI_ETH}\n
iface ${PRI_ETH} inet static"


## Below will generate /etc/network/interfaces primary NIC setting lines, like below sample:
#
#    auto eth0
#    iface eth0 inet static
#    address 1.2.3.4
#    netmask 255.255.255.0
#    gateway 1.1.1.1
#    dns-nameservers 4.3.2.1
#

for line in ${arr[@]}
do
     if [[ $(echo $line | grep ${IP_KEY}) != "" ]]
     then
          IP=${line##*${IP_KEY}} ## extract the IP from the line "adminIP=1.2.3.4"
          PRIM_ETH_CFG=$PRIM_ETH_CFG"\n    address $IP"
          echo IP:$IP
          if [[ -z "$IP" ]]; then
              echo "[Info] IP Address is blank in OVF ENV, Skip the Static IP Auto Setting. Exit.."
              exit 0
          fi;
     fi
     if [[ $(echo $line | grep ${DNS_KEY}) != "" ]]
     then
          DNS=${line##*${DNS_KEY}}
          echo DNS:$DNS
          PRIM_ETH_CFG=$PRIM_ETH_CFG"\n    dns-nameserver $DNS"
     fi
     if [[ $(echo $line | grep ${GW_KEY}) != "" ]]
     then
          GW=${line##*${GW_KEY}}
          echo Gateway:$GW
          PRIM_ETH_CFG=$PRIM_ETH_CFG"\n    gateway $GW"
     fi
     if [[ $(echo $line | grep ${MASK_KEY}) != "" ]]
     then
          MASK=${line##*${MASK_KEY}}
          echo NetMask:$MASK
          PRIM_ETH_CFG=$PRIM_ETH_CFG"\n    netmask $MASK"
     fi
done


########################################
#
# Assuming the original /etc/network/interfaces format is as below (take 14.04 as example):
#
#   auto lo
#   iface lo inet loopback
#   .....
#   auto eth0
#   iface eth0 inet xxxx
#   .....
#   auto eth1
#   iface eth1 inet xxxx
#   ...... 
#
# Below script will replace the old lines about "eth0" and replace with new lines in $PRIM_ETH_CFG
#######################################

target_file=/etc/network/interfaces

if [[ $(echo -e $PRIM_ETH_CFG | grep address ) != "" ]]
then
    # remove old primary seting( aka: remove lines from 'auto eth0' to 'auto eth1' )
    sed -i "/auto ${PRI_ETH}/,/auto ${SEC_ETH}/c\auto ${SEC_ETH}" ${target_file}
    # add new primary setting( use echo ${PRIM_ETH_CFG} to eliminate the newlines to make 'sed' happy
    sed -i "s/iface lo inet loopback/iface lo inet loopback\n$( echo ${PRIM_ETH_CFG})/"  ${target_file}
    # Force restart primary nic ###
    if [[ -f /run/network/ifup-${PRI_ETH}.pid ]]
    then
       DHCP_PID=$(cat /run/network/ifup-${PRI_ETH}.pid )
       echo "process ${DHCP_PID} is already running to get DHCP for ${PRI_ETH}. But because user assign static IP ${IP}, so force kill the DHCP process.."
       kill -9 ${DHCP_PID}
       sleep 2  # wait a while for clean killing
    fi
    ifdown ${PRI_ETH}
    ifup ${PRI_ETH}
else
    echo "can't detect IP address from OVF ENV, skip the ${PRI_ETH} configuration.."
fi


