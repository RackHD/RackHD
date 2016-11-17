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
    packer build -only=virtualbox-iso template-ubuntu-14.04.json

### Build vagrant box based on Ubuntu 16.04

    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer
    packer build -only=virtualbox-iso template-ubuntu-16.04.json

### To build locally (using pre-built debian packages - Ubuntu 14.04)

    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer
    export ANSIBLE_PLAYBOOK=rackhd_ci_builds
    ./HWIMO-BUILD

### To build VMware OVA/OVF

* Prerequisite: Install VMWare WorkStation(example , VMware Workstation 12.x ) and ovftool
```
    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer

    # if   build for Ubuntu 14.04
    export OS_VER=ubuntu-14.04
    # else, build for Ubuntu 16.04
    export OS_VER=ubuntu-16.04
```
* if build using pre-built debian packages on Bintray.com
```
    export ANSIBLE_PLAYBOOK=rackhd_ci_builds # tell packer to use rackhd_ci_builds.yml
```
* else , build from source code
```
    export ANSIBLE_PLAYBOOK=rackhd_local  # tell packer to use rackhd_local.yml

    export BUILD_TYPE=vmware      # tell packer to build -only=vmware-iso
    ./HWIMO-BUILD
```
* Tips:
  1. the OVA image build will be sit in rackhd/packer folder
  2. Packer can do the deployment automaticlly after OVA/OVF build (ovftool should be installed). just to add below lines in template-ubuntu-*.json as sub fields of "builders":
```
        "remote_type": "esx5",
        "remote_host": "$YOUR_ESXI_HOST_IP",
        "remote_datastore": "$YOUR_ESXI_DATASTORE_NAME",
        "remote_username": "$YOUR_ESXI_USER",
        "remote_password": "$YOUR_ESXI_PWS",
```

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

For more details on installation, please see the [Ubuntu source install guide](
http://rackhd.readthedocs.io/en/latest/rackhd/ubuntu_source_installation.html) or
the [Ubuntu package install guide](http://rackhd.readthedocs.io/en/latest/rackhd/ubuntu_package_installation.html)

### License notes

These scripts and templates are under an MPL-2.0 license due to leveraging
the content from https://github.com/hashicorp/atlas-packer-vagrant-tutorial.
To abide by the provided license, all files in this directory are shared
under the MPL-2.0 license, as described in the provided LICENSE file
