#!/bin/bash
#
# Copyright 2016, EMC, Inc.
#
# Restart each of the RackHD containers.
#

# enable to see script debug output
#set -x

echo "Restarting..."

for i in docker_mongo_1 docker_rabbitmq_1 docker_isc-dhcp-server_1 docker_files_1 docker_on-syslog_1 docker_on-tftp_1 docker_on-dhcp-proxy_1 docker_on-http_1 docker_on-taskgraph_1
do
	docker restart $i
done
