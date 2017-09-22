#!/bin/bash

set -e
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
    sleep 15
    timeout=`expr ${timeout} + 1`
  done
  set -e
  if [ ${timeout} == ${maxto} ]; then
    echo "Timed out waiting for RackHD API service (duration=`expr $maxto \* 10`s)."
    exit 1
  fi
}


CreateBridge(){
   # Set up br0
   brctl addbr br0
   ifconfig br0 promisc
   ifconfig br0 172.31.128.1
   brctl setfd br0 0
   brctl sethello br0 1
   brctl stp br0 no
   ifconfig br0 up
}


StartInfraSIM(){
    infrasim node start
}



CloneRackHDrepo(){
    pushd ~/
    if [ ! -d RackHD  ]; then
        git clone https://github.com/RackHD/RackHD.git
    fi
    popd
}

PullRackHD(){
    pushd ~/RackHD/docker
    docker-compose -f docker-compose.yml pull
    popd
}

StartRackHD(){
    echo "StartRackHD==========================================================================="
    pushd ~/RackHD/docker
    #UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=60)
    #https://github.com/docker/compose/issues/3633
    service docker restart
    sleep 5
    export DOCKER_CLIENT_TIMEOUT=400
    export COMPOSE_HTTP_TIMEOUT=400
    docker-compose -f docker-compose.yml up > /tmp/my.log &
    bg_pid=$!
    popd
}
bg_pid=0
service docker start
sleep 5
CreateBridge
CloneRackHDrepo
PullRackHD
#docker load -i /tmp/rackhd_docker_images.tar
StartRackHD
sleep 100
echo "========================================================================="
waitForAPI

#workaround, fixme, the latest docker images doesn't include rancher micro-kernel.so I will have to download it here.
pushd ~/RackHD/docker/files/mount/common
wget http://10.240.19.21/job/MasterCI/379/artifact/packages/on-imagebuilder/on-imagebuilder_2.23.0-20170919UTC-f4ea9ee_all.deb
dpkg -x on-imagebuilder_2.23.0-20170919UTC-f4ea9ee_all.deb .
cp var/renasar/on-http/static/http/common/* .
echo $(find ./)
popd

sleep 10
StartInfraSIM
wait $bg_pid
sleep 1000

