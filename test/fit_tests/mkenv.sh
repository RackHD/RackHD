#!/bin/bash

# Copyright 2015, EMC, Inc.

#
# Run this without options to create a virtual
# environment for the current git branch
#
# Override the default virtual enviornment name through
# the single argument to script:
#
# mkenv.sh <env_name>
#

PROG=${0}

# We need virtualenv from somewhere
virtualenv=`which virtualenv`
if [ ! -x "${virtualenv}" ]; then
    echo "location of virtualenv is unknown"
    exit 1
fi

# Set up env_name either from command line, else current git branch
if [ $# -eq 1 ]; then
    env_name=$1
else
    env_name=`git rev-parse --abbrev-ref HEAD`
fi

# Normalize env_name, replace '/' with '_'
env_name=${env_name//\//_}

# Our virtual environments are found within <toplevelgit>/env
#cd "$(git rev-parse --show-toplevel)"
export WORKON_HOME=`pwd`/env

# mkvirtualenv, OK if its already there
${virtualenv} --clear env/${env_name}

# activate the virtual environment
source env/${env_name}/bin/activate

# Use locally sourced pip configuration
export PIP_CONFIG_FILE=`pwd`/pip.conf

# Install all required packages
pip install -r requirements.txt

# Create local requirements (for example, pylint)
# pip install -r requirements_local.txt

# Generate a script that assists in switching environments
cat > myenv_${env_name} <<End-of-message
# *** Autgenerated file, do not commit to remote repository
export WORKON_HOME=${WORKON_HOME}
source env/${env_name}/bin/activate
End-of-message

echo ""
echo "${PROG}: complete, run the following to use '${env_name}' environment:"
echo
echo "source myenv_${env_name}"

exit 0
