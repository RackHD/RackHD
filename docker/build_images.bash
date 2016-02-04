#!/bin/bash

# enable to see script debug output
set -x

SCRIPT_DIR=$(cd $(dirname $0) && pwd)
echo "Rebuilding all docker images."

REPOS="on-core on-dhcp-proxy on-http on-statsd on-syslog on-tftp on-taskgraph"
for repo in ${REPOS}; do
    if [ -d "${SCRIPT_DIR}/../${repo}" ]; then
        pushd "${SCRIPT_DIR}/../${repo}"
          docker build -t rackhd/$repo --no-cache=false .
        popd
    fi
done
