# Packer Build Templates and scripts

These scripts and templates are for [packer](https://www.packer.io), and expect
it to be be installed locally. If you don't, you can install it on a Mac using
homebrew:

    brew install packer

or retrieving it from the download available at https://www.packer.io/downloads.html

## To build locally (using code from source)

The builds are pre-configured with post-processors to push the results to
ATLAS, and need relevant configuration set in environment variables to
enable:

    export ATLAS_USERNAME=rackhd
    export ATLAS_NAME=rackhd
    export ATLAS_TOKEN="..........................."

### Build vagrant box based on Ubuntu 14.04

    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer
    packer build -only=virtualbox-iso templates/template-ubuntu-14.04-source.json
    
### Build vagrant box based on Ubuntu 16.04

    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer
    packer build -only=virtualbox-iso templates/template-ubuntu-16.04-source.json
    
### To build locally (using pre-built debian packages - Ubuntu 14.04)

    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer
    packer build -only=virtualbox-iso templates/template-ubuntu-14.04-packages.json


### To build locally without publishing to atlas, use the `-notlas` variant.

    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer
    packer build -only=virtualbox-iso templates/template-ubuntu-14.04-source-noatlas.json


## Local install

You can do a local installation on a virtual machine or bare metal host
leveraging the same scripts that we use to make the VM with Packer. To do so,
you will need to install ansible on the machine where you want to do the
installation:

    sudo apt-get install ansible

and then to install from the bintray packages:

    ansible-playbook -c local -i "local," rackhd_package.yml

or from source:

    ansible-playbook -c local -i "local," rackhd_local.yml

For more details on installation, please see the [Ubuntu source install guide](http://rackhd.readthedocs.io/en/latest/rackhd/ubuntu_source_installation.html) 
or the [Ubuntu package install guide](http://rackhd.readthedocs.io/en/latest/rackhd/ubuntu_package_installation.html)

### License notes

These scripts and templates are under an MPL-2.0 license due to leveraging
the content from https://github.com/hashicorp/atlas-packer-vagrant-tutorial.
To abide by the provided license, all files in this directory are shared
under the MPL-2.0 license, as described in the provided LICENSE file
