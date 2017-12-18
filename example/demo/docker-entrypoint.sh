#!/bin/bash

# Copyright 2016, EMC, Inc.

# set -x
waitForAPI() {
  netstat -ntlp
  timeout=0
  maxto=60
  set +e
  url=http://localhost:9090/api/2.0/nodes
  while [ ${timeout} != ${maxto} ]; do
    wget --retry-connrefused --waitretry=1 --read-timeout=20 --timeout=15 -t 1 --continue ${url}
    if [ $? = 0 ]; then
      break
    fi
    sleep 10
    timeout=`expr ${timeout} + 1`
  done
  set -e
  if [ ${timeout} == ${maxto} ]; then
    echo "Timed out waiting for RackHD API service (duration=`expr $maxto \* 10`s)."
    exit 1
  fi
}

rm -f /var/lib/dhcp/dhchp.leases
touch /var/lib/dhcp/dhcpd.leases
chown root:root /var/lib/dhcp/dhcpd.leases
chmod 666 /var/lib/dhcp/dhcpd.leases

service isc-dhcp-server stop

mongod &
sleep 1
service rabbitmq-server start
sleep 1

# Set up br0
brctl addbr br0
ifconfig br0 promisc
ifconfig br0 172.31.128.1



pm2 status
pm2 logs > /var/log/rackhd.log &
pm2 start /rackhd.yml
sleep 15 && infrasim node start &
dhcpd -f -cf /etc/dhcp/dhcpd.conf -lf /var/lib/dhcp/dhcpd.leases --no-pid &

waitForAPI

pushd /RackHD/RackHD/test
rm -rf .venv/on-build-config
./mkenv.sh on-build-config
source myenv_on-build-config
python run_tests.py -test deploy/rackhd_stack_init.py -stack docker_local_run -numvms 1 -rackhd_host localhost -port 9090 -xunit -v 9
python run_tests.py -test tests -group smoke -stack docker_local_run -numvms 1 -rackhd_host localhost -port 9090 -xunit -v 9
deactive
popd
