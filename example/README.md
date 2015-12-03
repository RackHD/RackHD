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
and [Ansible](http://docs.ansible.com/ansible/intro_installation.html)
installed onto your system in order to use this script.


[ansible roles](https://github.com/RackHD/RackHD/tree/master/example/roles)

We also rely on the this projects structure of submodules to link the source
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

    $ pushd example/config/
    $ cp ./monorail_rack.cfg.example ./monorail_rack.cfg
    $ popd


Edits can be made to this new file to adjust the number of pxe clients created.

    $ pushd bin/
    $ ./monorail_rack


Now ssh into the RackHD server and start the services

    $ vagrant ssh
    $ sudo nf start


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

    vboxmanage startvm pxe-1 --type gui

You should see the VM PXE boot, get discovered, and ultimately get CoreOS
installed. The installation workflow included in the RackHD system installs
with a default SSH key that's included in our repositories. From the `example`
directory, you should be able to log in using:

`vagrant ssh`
    cp ~/src/on-http/data/rackhd_rsa ~/.ssh/id_rsa
    chmod 400 ~/.ssh/id_rsa
    ssh -i ~/src/on-http/data/rackhd_rsa core@172.32.128.2


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

For example, you can [manually download the ESXi installation ISO](https://www.vmware.com/go/download-vspherehypervisor) or download a [CentOS 7 LiveCD](http://buildlogs.centos.org/centos/7/isos/x86_64/CentOS-7-livecd-x86_64.iso).

Copy it into the `examples` directory and then you can unpack it in vagrant:

`vagrant ssh`:

    sudo mkdir /var/mirrors
    sudo python ~/src/on-http/data/templates/setup_iso.py \
    /vagrant/VMware-VMvisor-Installer-*.x86_64.iso \
    /var/mirrors --link=/home/vagrant/src

`mv ~/Downloads/CentOS*.iso ~/src/rackhd/example/`
`vagrant ssh`:

    sudo python ~/src/on-http/data/templates/setup_iso.py /vagrant/Cent*.iso \
    /var/mirrors --link=/home/vagrant/src





## HACKING THESE SCRIPTS

If you're having on this script or the [ansible roles](https://github.com/RackHD/RackHD/tree/master/example/roles) to change the
functionality, you can shortcut some of this process by just invoking
`vagrant provision` to use ansible to update the VM that's already been created.


### CHANGE NODE VERSION

Currently this example uses `n` (https://github.com/tj/n) to install node
version `0.10.40`. You can change what version of node is used by default by
logging into the Vagrant instance and using the `n` command:

    vagrant ssh
    sudo ~/n/bin/n <version>


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

### CHANGE WHAT BRANCH IS USED

To checkout to a different commit than what is referenced by git submodule,
edit the vagrant file (RackHD/example/Vagrantfile) to specify the `branch`
variable for the ansible provisioner. A commented out line exists in
`Vagrantfile` you can enable and edit.

    ansible.extra_vars = { branch: "master" }

## ENVIRONMENT BREAKDOWN

The monorail_rack script doesn't currently have the capability to shut down or
remove anything. To get rid of the RackHD server you can use:

    vagrant destroy

And you can remove the PXE vm(s) using the `vboxmanage` command, such as:

    vboxmanage unregistervm --delete pxe-1

## Running the web UI

We are experimenting with single page web UI applications within the repository
`on-web-ui` (https://github.com/rackhd/on-web-ui). That repository includes a
README and is set up to host the UI externally to the RackHD. Follow the
README instructions in that repository to run the application, and you can
change the settings while running to point to this instance of RackHD at
`https://localhost:9090/`
