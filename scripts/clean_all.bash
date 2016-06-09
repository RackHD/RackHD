#!/bin/bash

# enable to see script debug output
#set -x

SCRIPT_DIR=$(cd $(dirname $0) && pwd)
echo "Cleaning installation of all submodules"

REPOS="on-core on-tasks on-dhcp-proxy on-http on-statsd on-syslog on-tftp on-taskgraph on-wss"
for repo in ${REPOS}; do
    if [ -d "${SCRIPT_DIR}/../${repo}/node_modules" ]; then
        rm -rf "${SCRIPT_DIR}/../${repo}/node_modules"
    fi
done
