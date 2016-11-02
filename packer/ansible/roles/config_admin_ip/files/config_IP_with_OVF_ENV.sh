#!/bin/bash -e

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


vmtoolsd --cmd='info-get guestinfo.ovfEnv' >/tmp/ovf.xml
arr=$(getprops_from_ovfxml /tmp/ovf.xml)

IP_KEY="adminIP="
DNS_KEY="adminDNS="
GW_KEY="adminGateway="
MASK_KEY="adminNetmask="

if [[ ${#arr[@]} -eq 0  ]]
then
    return 0
fi

for line in ${arr[@]}
do
        echo $line
done

ETH0_CFG='# The primary network interface\
auto eth0\
iface eth0 inet static'



for line in ${arr[@]}
do
     if [[ $(echo $line | grep ${IP_KEY}) != "" ]]
     then
          IP=${line##*${IP_KEY}}
          echo IP:$IP
          ETH0_CFG=$ETH0_CFG"\n    address $IP"
     fi
     if [[ $(echo $line | grep ${DNS_KEY}) != "" ]]
     then
          DNS=${line##*${DNS_KEY}}
          echo DNS:$DNS
          ETH0_CFG=$ETH0_CFG"\n    dns-nameserver $DNS"
     fi
     if [[ $(echo $line | grep ${GW_KEY}) != "" ]]
     then
          GW=${line##*${GW_KEY}}
          echo Gateway:$GW
          ETH0_CFG=$ETH0_CFG"\n    gateway $GW"
     fi
     if [[ $(echo $line | grep ${MASK_KEY}) != "" ]]
     then
          MASK=${line##*${MASK_KEY}}
          echo NetMask:$MASK
          ETH0_CFG=$ETH0_CFG"\n    netmask $MASK"
     fi
done


if [[ $(echo -e $ETH0_CFG | grep address ) != "" ]]
then
    # remove old eth0 seting
    sed -i '/auto eth0/,/auto eth1/c\auto eth1' /etc/network/interfaces
    # add new eth0 setting
    sed -i "s/iface lo inet loopback/iface lo inet loopback\n$ETH0_CFG/"  /etc/network/interfaces
    # Force restart eth0 ###
    ifdown eth0
    ifup eth0
else
    echo "can't detect IP address from OVF ENV, skip the eth0 configuration.."
fi


