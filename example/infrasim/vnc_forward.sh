#/bin/bash

# Copyright (c) 2017-2018 Dell Inc. or its subsidiaries. All Rights Reserved.)

set +x
HOST_IP=`ifconfig eth0 | grep "inet addr" | awk 'BEGIN{FS=" "}{print $2}' | awk 'BEGIN{FS=":"}{print $2} '`
echo "Host eth0 IP is $HOST_IP"

for i in {100..128}
do
    NUMBER=$i
    IPADDR="172.31.128.$NUMBER"
    PORTNUM=`expr 28000 + $NUMBER`
    sudo iptables -P INPUT ACCEPT
    sudo iptables -P FORWARD ACCEPT
    sudo sysctl net.ipv4.ip_forward=1 > /dev/null
    sudo iptables -A PREROUTING -t nat -p tcp -d ${HOST_IP} --dport ${PORTNUM} -j DNAT --to ${IPADDR}:5901
    sudo iptables -t nat -A POSTROUTING -d $IPADDR -p tcp --dport 5901 -j MASQUERADE
    echo "Setting VNC port $PORTNUM for IP $IPADDR"
done

