#!/bin/bash

# enable to see script debug output
#set -x

SCRIPT_DIR=$(cd $(dirname $0) && pwd)
echo "Resetting all submodules to latest master branch"

REPOS="on-core on-tasks on-dhcp-proxy on-http on-statsd on-syslog on-tftp on-taskgraph on-wss on-imagebuilder"
for repo in ${REPOS}; do
    pushd "${SCRIPT_DIR}/../${repo}"
    git fetch --all --prune
    git reset --hard origin/master
    popd
done
