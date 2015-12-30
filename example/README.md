## DOCUMENTATION

The monorail_rack setup script is an easy "one button push" script to deploy
a 'virtual rack' using virtualbox. This emulates a RackHD server and some number
of virtual servers - using virtualbox PXE-booting VMs. Private virtual networks
simulate the connections between servers that would otherwise be on a switch
in a rack.

The virtual network `closednet` is set to our default subnet of 172.31.128.x
to connect DHCP and TFTP from RackHD to the PXE clients.

## PRE-REQS / SCRIPT EXPECTATIONS

We expect the latest version of git, [Vagrant](https://www.vagrantup.com/downloads.html),
[VirtualBox](https://www.virtualbox.org/wiki/Downloads),
and [Ansible](http://docs.ansible.com/ansible/intro_installation.html)
installed onto your system in order to use this script.

**NOTE**: Do not use Vagrant 1.8.0, as the private network settings don't appear
to be working correctly. Bug filed upstream with Vagrant at 
https://github.com/mitchellh/vagrant/issues/6730.


[ansible roles](https://github.com/RackHD/RackHD/tree/master/packer/ansible/roles)

We also rely on the projects structure of submodules to link the source
into the VM (through vagrant). The ansible roles are written to expect the
source to be autoloaded on the virtual machine with directory mappings
configured in Vagrantfile:

for example:

        ~/<repos directory>/RackHD/on-http/static/http/common/

The static files that RackHD uses can be built locally using the tools found in
the on-imagebuilder repository (https://github.com/RackHD/on-imagebuilder),
and this script will download the latest built versions that are stored in
bintray from that open source repository's outputs.

## SET UP INSTRUCTIONS

Clone RackHD repo to your local git directory.

    $ git clone https://github.com/RackHD/RackHD
    $ cd RackHD


Change into the directory `example`, create config and run the setup command:

    $ cd example
    $ cp config/monorail_rack.cfg.example config/monorail_rack.cfg


Edits can be made to this new file to adjust the number of pxe clients created.

    $ bin/monorail_rack


The `monorail_rack` script will auto-start all of the services by default, but you can
also run them manually if you prefer.

    $ vagrant ssh
    vagrant:~$ sudo nf start


## TESTING

Once you've started the services, the RackHD API will be available on your local
machine through port 9090. For example, you should be able to view the RackHD
API documentation that's set up with the service at http://localhost:9090/docs.

You can also interact with the APIs using curl from the command line of your
local machine.

To view the list of nodes that has been discovered:

    $ curl http://localhost:9090/api/1.1/nodes | python -m json.tool


View the list of catalogs logged into RackHD:

    $ curl http://localhost:9090/api/1.1/catalogs | python -m json.tool


(both of these should result in empty lists in a brand new installation)

### Install a default workflow for Virtualbox VMs and a SKUs definition

This example includes a workflow that we'll use when we identify a "virtualbox"
SKU with RackHD. This workflow sets up no-op out of band management settings
for a demo and triggers an installation of CoreOS as a default flow to run
once the "virtualbox" SKU has been identified. We'll load it into our library
of workflows:

    cd ~/src/rackhd/example
    # make sure you're in the example directory to reference the sample JSON correctly

    curl -H "Content-Type: application/json" \
    -X PUT --data @samples/virtualbox_install_coreos.json \
    http://localhost:9090/api/1.1/workflows


To enable that workflow, we also need to include a SKU definition that includes
the option of another workflow to run once the SKU has been identified. This
takes advantage of the `Graph.SKU.Discovery` workflow, which will attempt to
identify a SKU and run another workflow if specified.

    cd ~/src/rackhd/example
    # make sure you're in the example directory to reference the sample JSON correctly

    curl -H "Content-Type: application/json" \
    -X POST --data @samples/virtualbox_sku.json \
    http://localhost:9090/api/1.1/skus


View the current SKU definitions:

`curl http://localhost:9090/api/1.1/skus | python -m json.tool`

    [
        {
            "createdAt": "2015-11-21T00:46:04.068Z",
            "discoveryGraphName": "Graph.DefaultVirtualBox.InstallCoreOS",
            "discoveryGraphOptions": {},
            "id": "564fbecc1dee9e7d2f1d33ca",
            "name": "Noop OBM settings for VirtualBox nodes",
            "rules": [
                {
                    "equals": "VirtualBox",
                    "path": "dmi.System Information.Product Name"
                }
            ],
            "updatedAt": "2015-11-21T00:46:04.068Z"
        }
    ]

Once you've added those definitions, you can start up the test "PXE-1" virtual machine
using the command:

    VBoxManage startvm pxe-1 --type gui

You should see the VM PXE boot, get discovered, and ultimately get CoreOS
installed. The installation workflow included in the RackHD system installs
with a default SSH key that's included in our repositories. From the `example`
directory, you should be able to log in using:

`vagrant ssh`:

    cp ~/src/on-http/data/rackhd_rsa ~/.ssh/id_rsa
    chmod 0400 ~/.ssh/id_rsa
    ssh core@172.31.128.2


## USING OTHER WORKFLOWS

There are a number of workflows loaded by default in RackHD. Many of those
workflows rely on files or directories we don't package in this demonstration
in order to keep the setup times and resource usage small (or because we can't
legally redistribute some of the vendor specific tooling).

If you want to try some of the other workflows, especially related to installing
an OS, you'll need to add those files, and you'll need to work around the current
limitation that the vagrant demonstration doesn't have any out-of-band mechanism
for rebooting the `pxe-1` virtual machine.

### UNPACKING AN OS INSTALL ISO

For example, you can [manually download the ESXi installation ISO](https://www.vmware.com/go/download-vspherehypervisor)
or download a [CentOS 7 Installation ISO](http://mirror.umd.edu/centos/7/isos/x86_64/CentOS-7-x86_64-DVD-1503-01.iso).

Copy it into the `examples` directory and then you can unpack it in vagrant:

`vagrant ssh`:

    sudo mkdir /var/mirrors
    sudo python ~/src/on-http/data/templates/setup_iso.py /vagrant/VMware-VMvisor-Installer-*.x86_64.iso /var/mirrors --link=/home/vagrant/src


`vagrant ssh`:

    cd /tmp
    wget http://mirror.umd.edu/centos/7/isos/x86_64/CentOS-7-x86_64-DVD-1503-01.iso
    # 4GB
    sudo python ~/src/on-http/data/templates/setup_iso.py /tmp/CentOS-7-x86_64*.iso /var/mirrors --link=/home/vagrant/src

The CentOS installer wants a bit more memory easily available for the
installation than we default our test VM towards, so we recommend updating
it to 2GB of RAM with the following commands:

    VBoxManage controlvm poweroff pxe-1
    VBoxManage modifyvm pxe-1 --memory 2048;
    VBoxManage controlvm poweron pxe-1

And then invoking the workflow to install CentOS you just unpacked

    cd ~/src/rackhd/example
    # make sure you're in the example directory to reference the sample JSON correctly

    curl -H "Content-Type: application/json" \
    -X POST --data @samples/centos_iso_boot.json \
    http://localhost:9090/api/1.1/nodes/566af6c77c5de76d1530d1f3/workflows | python -m json.tool

You can see the example stanza for posting a workflow with options at
[samples/centos_iso_boot.json](samples/centos_iso_boot.json).

Some of the workflows (like OS install) are set to allow for additional
options during installation as well. For example, at
[samples/centos_iso_kvm_boot.json](samples/centos_iso_kvm_boot.json) we
include an additional option that is rendered by the template to install
the KVM packages after the default installation.

**NOTE** because this demonstration setup uses Virtualbox, there is no out
of band management to trigger the machine to reboot. Once the workflow
has been activated, the VM will need to be rebooted manually for the
workflow to operate.

## HACKING THESE SCRIPTS

The vagrant image is built using [packer](https://packer.io/) with the
configuration in https://github.com/RackHD/RackHD/tree/master/packer and
provisioned using  [ansible roles](https://github.com/RackHD/RackHD/tree/master/packer/ansible/roles).
You can tweak those roles and make your own builds either locally or using
packer and [atlas](http://atlas.hashicorp.com).


### CONFIGURATION FILE

```
# monorail_rack.cfg
# used to customize default deployment
# edit $pxe_count to change the amount of virtualbox PXE-booting clients are created when running
# the monorail_rack setup script.

# deployment variables
pxe_count=1
```

Changing the number of `pxe_count` within the running configuration script will
effect how many headless pxe clients are created when running the monorail_rack
setup script.

Please note, and example configuration file is provided and you must copy that
file to a new file with the same name excluding the .example extension.

## ENVIRONMENT BREAKDOWN

The monorail_rack script doesn't currently have the capability to shut down or
remove anything. To get rid of the RackHD server you can use:

    vagrant destroy

And you can remove the PXE vm(s) using the `VBoxManage` command, such as:

    VBoxManage unregistervm --delete pxe-1

## Running the web UI

We are experimenting with single page web UI applications within the repository
`on-web-ui` (https://github.com/rackhd/on-web-ui). That repository includes a
README and is set up to host the UI externally to the RackHD. Follow the
README instructions in that repository to run the application, and you can
change the settings while running to point to this instance of RackHD at
`https://localhost:9090/`
