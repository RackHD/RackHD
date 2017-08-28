# Packer Build Templates and scripts

These scripts and templates are for [packer](https://www.packer.io), and expect
it to be be installed locally. If you don't, you can install it on a Mac using
homebrew:

    brew install packer

or retrieving it from the download available at https://www.packer.io/downloads.html

## To Build Vagrant Box

### Prerequisite
- clone code
```
    git clone https://github.com/rackhd/rackhd
    cd rackhd/packer
```
- if build based on Ubuntu 14.04
```
    export OS_VER=ubuntu-14.04
```
- else, if build based on Ubuntu 16.04
```
    export OS_VER=ubuntu-16.04
```
- if to upload vagrant box to ATLAS
The builds are pre-configured with post-processors to push the results to ATLAS, and need relevant configuration set in environment variables to enable:
```
    export ATLAS_USERNAME=rackhd
    export ATLAS_NAME=rackhd
    export ATLAS_TOKEN="..........................."
```
- if you don't want to upload the box to ATLAS, you can follow below suggestion to remove the "post-processors" in json file:
```
jq 'del(.["post-processors", "push"])' /tmp/template-${OS_VER}.json > template-${OS_VER}.json
```

### To build locally (install RackHD from source code)

    export ANSIBLE_PLAYBOOK=rackhd_local # tell packer to use rackhd_local.yml
    export BUILD_TYPE=virtualbox
    ./HWIMO-BUILD

### To build using pre-built debian packages

    export ANSIBLE_PLAYBOOK=rackhd_package
    export BUILD_TYPE=virtualbox
    ./HWIMO-BUILD

## To build VMware OVA/OVF

### Prerequisite
- use VMWare Tools

 Option #1:  Install VMWare WorkStation locally on the same OS where the packer build runs ( example: install VMware Workstation 12.x )
 Note: the licensed version of VMWare WorkStation is required, to enable the 2-stages vmware build.(iso -> temp_vmx -> final_ova )

 Option #2:  To use a remote VMware vSphere Hypervisor to build your VM, just to add below lines in template-ubuntu-*.json as sub fields of "builders"(refer to https://www.packer.io/docs/builders/vmware-iso.html for more info.)

```
        "remote_type": "esx5",
        "remote_host": "$YOUR_ESXI_HOST_IP",
        "remote_datastore": "$YOUR_ESXI_DATASTORE_NAME",
        "remote_cache_directory": "$YOUR_REMOTE_ISO_CACHE_DIR"
        "remote_username": "$YOUR_ESXI_USER",
        "remote_password": "$YOUR_ESXI_PWS",
```
- install ovftool

refer to VMWare documents to install ovftool. it will be used to convert between ovf and ova. and also can used to deploy OVA to remote ESXi.

- clone code
```
       git clone https://github.com/rackhd/rackhd
       cd rackhd/packer
```
- if   build based on Ubuntu 14.04
```
       export OS_VER=ubuntu-14.04
```
- else, build based on Ubuntu 16.04
```
       export OS_VER=ubuntu-16.04
```
### To build locally (using code from source)
```
    export ANSIBLE_PLAYBOOK=rackhd_local
    export BUILD_TYPE=vmware
    ./HWIMO-BUILD
```
###  To build using pre-built debian packages on Bintray.com
```
    export ANSIBLE_PLAYBOOK=rackhd_ci_builds
    export BUILD_TYPE=vmware
    ./HWIMO-BUILD
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
