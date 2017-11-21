#!/bin/bash -x
# Copyright © 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

DOCKER_IMG_NAME="infrasim/infrasim-compute" 
DOCKER_IMG_TAG="3.5.1"
NAME="infrasim" #Container Name
PORT="5901" #Host port which is bind to container port
CONFIG="default.yml" #config file for the virtual node

help()
{
    echo "start-node.sh - Start an Infrasim vNode container"
    echo "Usage: ./start-node.sh [options]"
    echo "Options:"
    echo "-p The host port used to map the container's vnc port"
    echo "-n Set the name for the container"
    echo "-c The config file to use for the virtual node"
}

while getopts "hp:n:c:" args;do
    case ${args} in
        h)
            help
	        exit 0
            ;;
        p)
            PORT=$OPTARG
            ;;
        n)
            NAME=$OPTARG
            ;;
        c)
            CONFIG=$OPTARG
            ;;
        *)
            help
	        exit 1
	        ;;
    esac
done	

## Prepare for docker environment
which docker
if [ $? -ne 0 ]; then
    echo "Docker not installed, please install it manually then re-run the script."
    exit 1
fi

## Setup docker container 
docker ps -a |grep -w $NAME
if [ $? -eq 0 ]; then
    echo "Going to stop and remove container $NAME because it's running."
    docker container stop $NAME
    docker container rm $NAME
fi

docker pull $DOCKER_IMG_NAME:$DOCKER_IMG_TAG
if [ $? -ne 0 ]; then
    echo "Failed to pull $DOCKER_IMG_NAME:$DOCKER_IMG_TAG from dockerhub."
    exit 1
fi

docker run --privileged -p $PORT:5901 -dit --name $NAME $DOCKER_IMG_NAME:$DOCKER_IMG_TAG /bin/bash

## Use Pipework to set up the vNode network
sudo ./pipework/pipework ovs-br0 -i eth1 $NAME dhclient
docker exec $NAME brctl addbr br0
docker exec $NAME brctl addif br0 eth1
IP=$(docker exec $NAME ifconfig eth1 | awk '/inet addr/{print substr($2,6)}')
if [ $? -ne 0 ]; then
    echo "No DHCP service, please check DHCP server."
else
    echo "IP assigned for eth1 is: $IP"
    docker exec $NAME ifconfig eth1 0.0.0.0
    docker exec $NAME ifconfig br0 $IP
fi

## Copy the config file to the container
docker cp $CONFIG $NAME:/root/.infrasim/.node_map/default.yml

## Start the node
docker exec $NAME infrasim node start
