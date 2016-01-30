#!/bin/bash

# enable to see script debug output
#set -x

SCRIPT_DIR=$(cd $(dirname $0) && pwd)
echo "Resetting all submodules to docker branch"

git submodule init
git submodule update --recursive

REPOS="on-core on-tasks on-dhcp-proxy on-http on-syslog on-tftp on-taskgraph"
for repo in ${REPOS}; do
    pushd "${SCRIPT_DIR}/../${repo}"
        git remote add rp "https://github.com/rolandpoulter/${repo}"
        git fetch --all --prune
        git reset --hard rp/docker
    popd
done
