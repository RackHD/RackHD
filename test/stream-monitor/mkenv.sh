#!/bin/bash

# Copyright 2016, EMC, Inc.

#
# Run this without options to create a virtual
# environment for a specific name, a default name, or git-branch
# based name.
#
# By default (no argument), the base environment name will be 'fit'
#  If an argument is passed, the base name will be that value _except_
#  If the argument is 'git', the base name will be the git-branch
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
    if [ "$1" == "git" ]; then
	env_name=`git rev-parse --abbrev-ref HEAD`
    else
	env_name=$1
    fi
else
    env_name='fit'
fi

# Normalize env_name, replace '/' with '_'
env_name=${env_name//\//_}

# Our virtual environments are found within <toplevelgit>/.venv
export WORKON_HOME=`pwd`/.venv

# mkvirtualenv, OK if its already there
${virtualenv} --clear .venv/${env_name}

# activate the virtual environment
source .venv/${env_name}/bin/activate

# Use locally sourced pip configuration
export PIP_CONFIG_FILE=`pwd`/pip.conf

# Update local-pip to latest
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# Create local requirements (for example, pylint)
# pip install -r requirements_local.txt

# Generate a script that assists in switching environments
cat > myenv_${env_name} <<End-of-message
# *** Autgenerated file, do not commit to remote repository
export WORKON_HOME=${WORKON_HOME}
source .venv/${env_name}/bin/activate
End-of-message

echo ""
echo "${PROG}: complete, run the following to use '${env_name}' environment:"
echo
echo "source myenv_${env_name}"

exit 0
