# Packer Build Templates and scripts

These scripts and templates are for [packer](https://www.packer.io), and expect
it to be be installed locally. If you don't, you can install it on a Mac using
homebrew:

    brew install packer

or retrieving it from the download available at https://www.packer.io/downloads.html
The builds are pre-configured with post-processors to push the results to
ATLAS, and need relevant configuration set in environment variables to
enable:

    export ATLAS_USERNAME=${USER}
    export ATLAS_NAME=rackhd
    export ATLAS_TOKEN="..........................."

## To build locally (using code from source)

### Build vagrant box based on Ubuntu 14.04

    packer build -only=virtualbox-iso template-ubuntu-14.04.json

### Build vagrant box based on Ubuntu 16.04

    packer build -only=virtualbox-iso template-ubuntu-16.04.json

## To build locally (using pre-built debian packages)

    packer build -only=virtualbox-iso template-packages.json


## To use ansible roles to install locally

    sudo apt-get install ansible

and then:

    ansible-playbook -c local -i "local," rackhd_package.yml

or

    ansible-playbook -c local -i "local," rackhd_local.yml

### License notes

These scripts and templates are under an MPL-2.0 license due to leveraging
the content from https://github.com/hashicorp/atlas-packer-vagrant-tutorial.
To abide by the provided license, all files in this directory are shared
under the MPL-2.0 license, as described in the provided LICENSE file
