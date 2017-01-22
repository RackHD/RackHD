#!/bin/bash

PWD=$(pwd)
MYDIR=${1:-$PWD}
if [ ! -d $MYDIR ]; then
    echo "[Error] working directory=$MYDIR doesn't exist"
    exit -1
fi

pushd $MYDIR

WORKDIR=$(pwd)  # Absolute Path


set -e
set -x

BRANCH=${2:-master} # can be a tag like 1.0.0



NODE_CORE_REPOS=("on-core" "on-tasks" "di.js" )
NODE_OTHER_REPOS=("on-http" "on-taskgraph" "on-dhcp-proxy" "on-tftp" "on-syslog" )
NODE_REPOS=("${NODE_CORE_REPOS[@]}" "${NODE_OTHER_REPOS[@]}")
OTHER_REPOS=( "on-wss" "on-tools" "on-imagebuilder" "RackHD")
REPOS=( "${NODE_REPOS[@]}"  "${OTHER_REPOS[@]}" )
#GITHUB="https://eos2git.cec.lab.emc.com/RackHD" # https://github.com/RackHD
GITHUB="https://github.com/RackHD"


echo "[Info] Clone RackHD repos, and checkout to  branch ${BRANCH}"


for r in ${REPOS[@]}; do
    rm ${r} -rf
    git clone ${GITHUB}/${r}.git
    pushd ${r}
    git fetch --all --prune --tags
    if [ -z $BRANCH ]; then
        git checkout ${BRANCH}
    fi
    popd
done

for r in ${NODE_REPOS[@]}; do
    pushd ${r}
    npm install --production
    popd
done

echo "[Info] Make common static directory & generate Docs"
HTTP_STATIC_FOLDER=on-http/static/http
TFTP_STATIC_FOLDER=on-tftp/static/tftp
mkdir -p $HTTP_STATIC_FOLDER
mkdir -p $TFTP_STATIC_FOLDER
mkdir -p on-http/static/http/common
pushd on-http
npm install apidoc
npm run apidoc
npm run taskdoc
popd



echo "[Info] Download Static Images"
HTTP_BASE_URL=https://bintray.com/artifact/download/rackhd/binary/builds/
TFTP_BASE_URL=https://bintray.com/artifact/download/rackhd/binary/builds/
SYSL_BASE_URL=https://bintray.com/artifact/download/rackhd/binary/syslinux/
HTTP_STATIC_FILES=( discovery.overlay.cpio.gz base.trusty.3.16.0-25-generic.squashfs.img initrd.img-3.16.0-25-generic vmlinuz-3.16.0-25-generic )
TFTP_STATIC_FILES=( monorail.ipxe monorail-undionly.kpxe monorail-efi32-snponly.efi monorail-efi64-snponly.efi monorail.intel.ipxe )
SYSL_STATIC_FILES=( undionly.kkpxe )
for f in ${HTTP_STATIC_FILES[@]}; do
    wget ${HTTP_BASE_URL}/${f}  ${HTTP_STATIC_FOLDER}/${f}
done
for f in ${TFTP_STATIC_FILES[@]}; do
    wget ${TFTP_BASE_URL}/${f}  ${TFTP_STATIC_FOLDER}/${f}
done
for f in ${SYSL_STATIC_FILES[@]}; do
    wget ${SYSL_BASE_URL}/${f}  ${SYSL_STATIC_FOLDER}/${f}
done


echo "[Info] Move the on-core/on-tasks into each dependent repo's node_modueles..."
for r in ${NODE_OTHER_REPOS[@]}; do
    pushd ${r}/node_modules/
    #remove the on-core/on-tasks, and replace by a link to local folder
    for dep in ${NODE_CORE_REPOS[@]}; do
       rm ${dep} -rf
       ln -s ../../${dep}     ${dep}
    done
    popd
done

echo "[Info] npm install pm2...."

sudo npm install -g pm2

echo  "
apps:
  - script: index.js
    name: on-taskgraph
    cwd: ${WORKDIR}/on-taskgraph
  - script: index.js
    name: on-http
    cwd: ${WORKDIR}/on-http
  - script: index.js
    name: on-dhcp
    cwd: ${WORKDIR}/on-dhcp-proxy
  - script: index.js
    name: on-syslog
    cwd: ${WORKDIR}/on-syslog
  - script: index.js
    name: on-tftp
    cwd: ${WORKDIR}/on-tftp
" > rackhd-pm2-config.yml

echo "[Info] Starts RackHD with pm2"

echo "[Done!] Please start RackHD with command line -->  sudo pm2 start rackhd-pm2-config.yml "

popd



