#!/bin/bash
#
# Copyright 2016, EMC, Inc.
#
# Start the RackHD containers, satisfying the dependencies as they
# are specified in the docker-compose.yml file. Use this script
# in those circumstances where docker-compose is not available
# or desired. Be careful to keep this script up-to-date with any
# changes made to docker-compose.yml.
#
# Related scripts:
#	follow_services.bash, stop_services.bash, restart_services.bash,
#	remove_services.bash
#

# enable to see script debug output
#set -x

#
#volumes:
#  dhcp-leases:
#    external: false
#

echo "Creating shared volumes..."
docker volume create --name docker_dhcp-leases

echo "Starting..."

#
#  files:
#    build: "./files"
#    image: "rackhd/files"
#    network_mode: "host"
#    privileged: true
#    volumes:
#      - "./files/mount:/RackHD/files"
#
echo "    files..."
docker run --privileged=true --net="host" --name docker_files_1 -d -v /RackHD/docker/files/mount:/RackHD/files rackhd/files > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  dhcp: # 67/udp
#    image: rackhd/isc-dhcp-server
#    build: "./dhcp"
#    network_mode: "host"
#    privileged: true
#    volumes:
#      - "dhcp-leases:/var/lib/dhcp"
#      - "./dhcp/config:/etc/dhcp"
#      - "./dhcp/defaults:/etc/defaults"
#
echo "    isc-dhcp-server..."
docker run --privileged=true --net="host" --name docker_isc-dhcp-server_1 -d -v docker_dhcp-leases:/var/lib/dhcp -v /RackHD/docker/dhcp/config:/etc/dhcp -v /RackHD/docker/dhcp/defaults:/etc/defaults rackhd/isc-dhcp-server > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  mongo: # 27017
#    image: mongo:latest
#    network_mode: "host"
#    privileged: true
#
echo "    mongo..."
docker run --privileged=true --net="host" --name docker_mongo_1 -d mongo:latest > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  rabbitmq: # 5672, 15672
#    image: rabbitmq:management
#    network_mode: "host"
#    privileged: true
#
echo "    rabbitmq..."
docker run --privileged=true --net="host" --name docker_rabbitmq_1 -d rabbitmq:management > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  http: # 9090, 9080
#    build: "../on-http"
#    depends_on:
#      - files
#      - mongo
#      - rabbitmq
#    image: rackhd/on-http:latest
#    network_mode: "host"
#    privileged: true
#    volumes:
#      - "./files/mount/common:/RackHD/on-http/static/http/common"
#      - "./monorail:/opt/monorail"
#
echo "    on-http..."
docker run --privileged=true --net="host" --name docker_on-http_1 -d -v /RackHD/docker/files/mount/common:/RackHD/on-http/static/http/common -v /RackHD/docker/monorail:/opt/monorail rackhd/on-http:latest > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  dhcp-proxy: # 68/udp, 4011
#    build: "../on-dhcp-proxy"
#    depends_on:
#      - dhcp
#      - mongo
#      - rabbitmq
#    image: rackhd/on-dhcp-proxy:latest
#    network_mode: "host"
#    privileged: true
#    volumes:
#      - "./monorail:/opt/monorail"
#
echo "    on-dhcp-proxy..."
docker run --privileged=true --net="host" --name docker_on-dhcp-proxy_1 -d -v /RackHD/docker/monorail:/opt/monorail rackhd/on-dhcp-proxy:latest > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  syslog: # 514/udp
#    build: "../on-syslog"
#    depends_on:
#      - mongo
#      - rabbitmq
#    image: rackhd/on-syslog:latest
#    network_mode: "host"
#    privileged: true
#    volumes:
#      - "./monorail:/opt/monorail"
#
echo "    on-syslog..."
docker run --privileged=true --net="host" --name docker_on-syslog_1 -d -v /RackHD/docker/monorail:/opt/monorail rackhd/on-syslog:latest > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  tftp: # 69/udp
#    build: "../on-tftp"
#    depends_on:
#      - files
#      - mongo
#      - rabbitmq
#      - syslog
#    image: rackhd/on-tftp:latest
#    network_mode: "host"
#    privileged: true
#    volumes:
#      - "./files/mount:/RackHD/on-tftp/static/tftp"
#      - "./monorail:/opt/monorail"
#
echo "    on-tftp..."
docker run --privileged=true --net="host" --name docker_on-tftp_1 -d -v /RackHD/docker/files/mount:/RackHD/on-tftp/static/tftp -v /RackHD/docker/monorail:/opt/monorail rackhd/on-tftp:latest > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

#
#  taskgraph:
#    build: "../on-taskgraph"
#    depends_on:
#      - dhcp
#      - mongo
#      - rabbitmq
#      - syslog
#    image: rackhd/on-taskgraph:latest
#    network_mode: "host"
#    privileged: true
#    volumes:
#      - "dhcp-leases:/var/lib/dhcp"
#      - "./monorail:/opt/monorail"
#
echo "    on-taskgraph..."
docker run --privileged=true --net="host" --name docker_on-taskgraph_1 -d -v docker_dhcp-leases:/var/lib/dhcp -v /RackHD/docker/monorail:/opt/monorail rackhd/on-taskgraph:latest > /dev/null
if [ $? -ne 0 ]; then
	echo "Failed"
	exit
fi

echo "Done."

