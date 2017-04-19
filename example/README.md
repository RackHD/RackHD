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
to be working correctly. Later versions (Vagrant 1.8.1) resolved this issue.

We utilize
[ansible roles](https://github.com/RackHD/RackHD/tree/master/packer/ansible/roles)
with a [packer template](https://github.com/RackHD/RackHD/blob/master/packer/template.json)
to pre-build the RackHD VM. If you want to create your own packaged
installation of RackHD from source, you can start with this for guidance.

The static files that RackHD uses can be built locally using the tools found in
the on-imagebuilder repository (https://github.com/RackHD/on-imagebuilder),
and this script will download the latest built versions that are stored in
bintray from that open source repository's outputs.

## SET UP INSTRUCTIONS

Clone RackHD repo to your local machine.

    git clone https://github.com/RackHD/RackHD
    cd RackHD
    cd example
    # create the RackHD instance.
    vagrant up dev
    # start the RackHD services
    vagrant ssh dev -c "sudo pm2 start rackhd-pm2-config.yml"

### LOCAL SOURCE

If you set the environment variables `WORKSPACE` and then either `REPO` and/or
`CONFIG_DIR`, the Vagrant instance for RackHD will attempt to mount the relevant
repository locally from your machine. For example, if you had alternative source
for on-http that you wanted to use, checked out at /Users/heckj/src/on-http,
you could use:

    export WORKSPACE=/Users/heckj/src
    export REPO=on-http

to mount that directory within the RackHD Vagrant instance referencing your
local source.


## Validating RackHD is operational

Once you've started the services, the RackHD API will be available on your local
machine through port 9090. For example, you should be able to view the RackHD 1.1
API documentation that's set up with the service at http://localhost:9090/docs.
The RackHD 2.0 and Redfish API online documentation are available at
http://localhost:9090/swagger-ui/.

You can also utilize the Github pages hosted version of the RackHD developer GUI
by opening your browser to http://rackhd.github.io/on-web-ui. The defaults for
this UI will attempt to connect to your locally running instance.

You can also interact with the APIs using curl from the command line of your
local machine.

To view the list of nodes that has been discovered:

    curl http://localhost:9090/api/1.1/nodes | python -m json.tool


View the list of catalogs logged into RackHD:

    curl http://localhost:9090/api/1.1/catalogs | python -m json.tool


(both of these should result in empty lists in a brand new installation)

To view a list of all the existing workflows already in the RackHD definitions:

    curl http://localhost:9090/api/1.1/workflows/library/* | python -m json.tool


### Authentication

An optional authenticated northbound endpoint will be enabled on port 9093.
Login with the default username/password to retrieve the login token:

    curl -k https://localhost:9093/login -X POST \
    -H 'Accept:application/json' -H 'Content-Type:application/json' \
    -d '{"username":"admin","password":"admin123"}' | python -m json.tool

    {
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoiYWRtaW4iLCJpYXQiOjE0NjYxMDQ2OTksImV4cCI6MTQ2NjE5MTA5OX0.qRVEP66zCsoOGTXmtbCnMPZ7Pj-E006TKLUNPc_Mk6k"
    }


A PATCH to the /users/<user> API can be made to change the default user password:

    curl -k https://localhost:9093/api/2.0/users/admin -X PATCH \
    -H "Accept:application/json" -H 'Authorization: JWT <token>' \
    -d '{"password":"<new_password>"}'


A POST to the /users API can be made to add a user.  The role "Administrator" for read/write and "ReadOnly" for readonly access are valid.

    curl -k https://localhost:9093/api/2.0/users -X POST \
    -H "Accept:application/json" -H 'Authorization: JWT <token>' \
    -d '{"username":"<username>", "password":"<password>", "role": "Administrator"}'

### Install a default workflow for virtual Quanta VMs and a SKUs definition

This example includes a workflow that we'll use when we identify a "virtual quanta"
SKU with RackHD. This workflow sets up no-op out of band management settings
for a demo and triggers an installation of CentOS as a default flow to run
once the "virtualbox" SKU has been identified. We'll load it into our library
of workflows:

    cd ~/src/rackhd/example
    # make sure you're in the example directory to reference the sample JSON correctly

    curl -H "Content-Type: application/json" \
    -X PUT --data @samples/vQuanta_default_workflow.json \
    http://localhost:9090/api/2.0/workflows/graphs

To enable that workflow, we also need to include a SKU definition that includes
the option of another workflow to run once the SKU has been identified. This
takes advantage of the `Graph.SKU.Discovery` workflow, which will attempt to
identify a SKU and run another workflow if specified.

    cd ~/src/rackhd/example
    # make sure you're in the example directory to reference the sample JSON correctly

    curl -H "Content-Type: application/json" \
    -X POST --data @samples/vQuanta_d51_sku.json \
    http://localhost:9090/api/2.0/skus


View the current SKU definitions:

`curl http://localhost:9090/api/2.0/skus | python -m json.tool`

    [
        {
            "createdAt": "2016-04-28T20:05:56.975Z",
            "discoveryGraphName": "Graph.DefaultVQuanta.InstallCentOS",
            "discoveryGraphOptions": {},
            "id": "57226d24fc06c6b414cf1027",
            "name": "vQuanta D51 SKU",
            "rules": [
                {
                    "equals": "D51B-2U (dual 10G LoM)",
                    "path": "dmi.System Information.Product Name"
                },
                {
                    "equals": "SerialNumber",
                    "path": "dmi.System Information.Serial Number"
                }
            ],
            "updatedAt": "2016-04-28T20:05:56.975Z"
        }
    ]

### Set up and activate the virtual hardware

We can use a simulated Quanta D51 levering [InfraSim](https://github.com/InfraSim/InfraSim)
to work with RackHD APIs. To set up and active this machine:

    vagrant up quanta_d51

You can see the Quanta d51 control with the vBMC quanta simulator by using VNC
to connect to 127.0.0.1:15901 (or 127.0.0.1 display 10001). You can log into
the VM hosting this simulation with the default credentials of "root"/"root"
and the IPMI credentials that it's providing on `closednet` are "admin"/"admin".


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
or download a [CentOS 7 Installation ISO](http://mirrors.mit.edu/centos/7/isos/x86_64/CentOS-7-x86_64-DVD-1611.iso).

**NOTE:** Below, we show two methods (A&B) of ensuring we have the iso file properly placed to be referenced by our helper script.

Mirror Site: http://mirror.centos.org/centos/7/os/x86_64/

---
**A.** Copy the iso into the `examples` directory within the RackHD source directory and then unpack it in using Vagrant's access to the local filesystem:

Copy it into the `examples` directory and then you can unpack it in vagrant:

`cd ~/src/rackhd/examples`

`wget http://mirrors.mit.edu/centos/7/isos/x86_64/CentOS-7-x86_64-DVD-1611.iso`
_NOTE_: this is a 4GB download.

`vagrant ssh dev`:

    sudo mkdir -p /var/mirrors
    sudo python ~/src/on-tools/scripts/setup_iso.py /vagrant/CentOS-7-x86_64-DVD-1611.iso /var/mirrors --link=/home/vagrant/src


---
**B.** Below shows downloading an iso file directly onto the server.

**NOTE:** We continue with a CentOS install to complete the instructions.

`vagrant ssh dev`:

    sudo mkdir -p /var/mirrors
    cd /tmp
    # 4GB download!!
    wget http://mirrors.mit.edu/centos/7/isos/x86_64/CentOS-7-x86_64-DVD-1611.iso
    cd ~
    sudo mkdir src
    cd src
    sudo git clone https://github.com/RackHD/on-tools.git
    sudo mkdir -p on-http/static/http
    sudo mkdir -p on-tftp/static/tftp
    sudo python ~/src/on-tools/scripts/setup_iso.py /tmp/CentOS-7-x86_64*.iso /var/mirrors --link=/home/vagrant/src
    cd /opt/monorail/static/http
    sudo ln -s ~/src/on-http/static/http/Centos

And then invoking the workflow to install CentOS you just unpacked

    # make sure you're in the example directory to reference the sample JSON correctly and
    # use the correct nodeid.

    cd ~/src/rackhd/example

    # first post obm settings (out of band management) for the node. In this example we
    # set this to be empty because our pxe-client has no obm.

    curl -H "Content-Type: application/json" \
    -X POST —-data @samples/noop_body.json \
    http://localhost:9090/api/2.0/nodes/<insertTheNodeId>/obm | python -m json.tool

    # next post the workflow

    curl -H "Content-Type: application/json" \
    -X POST --data @samples/centos_iso_boot.json \
    http://localhost:9090/api/2.0/nodes/<insertTheNodeId>/workflows | python -m json.tool

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
# edit $PXE_COUNT to change the amount of virtualbox PXE-booting clients are created when running
# the monorail_rack setup script.

# deployment variables
PXE_COUNT=1
```

Changing the number of `PXE_COUNT` within the running configuration script will
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

# Running Integration Tests

* create the vagrant demo setup and update code to the latest version

`vagrant ssh dev`:

    cd ~/src
    ./scripts/clean_all.bash && ./scripts/reset_submodules.bash && ./scripts/link_install_locally.bash
    cd ~
    sudo pm2 start rackhd-pm2-config.yml

* log in to the same VM with another shell and start the tests

`vagrant ssh dev`:

    cd ~/src/test
    virtualenv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python run.py

* start a PXE booting VM on the `closednet` to trigger the tests to complete

    vagrant up quanta_d51
