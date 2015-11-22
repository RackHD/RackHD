## DOCUMENTATION

The monorail_rack setup script is an easy "one button push" script to deploy
a 'virtual rack' using virtualbox. This emulates a RackHD server and some number
of virtual servers - using virtualbox PXE-booting VMs. Private virtual networks
simulate the connections between servers that would otherwise be on a switch
in a rack.

The virtual network `closednet` is set to our default subnet of 172.31.128.x
to connect DHCP and TFTP from RackHD to the PXE clients.

## PRE-REQS / SCRIPT EXPECTATIONS

We expect the latest version of git, Vagrant, and Ansible installed onto your
system in order to use this script.

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
SKU with RackHD. We'll load it into our library of workflows:

    curl -H "Content-Type: application/json" -X PUT \
    --data @samples/virtualbox_install_coreos.json \
    http://localhost:9090/api/1.1/workflow

We also include the sku definition. RackHD sku support includes a mechanism that
will run a workflow when a SKU is identified. In this case, the example uses the
workflow we just loaded into the library.

    curl -H "Content-Type: application/json" \
    -X POST --data @samples/virtualbox_sku.json \
    http://localhost:9090/api/1.1/skus

View the current SKU definitions:

    $ curl http://localhost:9090/api/1.1/skus | python -m json.tool
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

## HACKING THESE SCRIPTS

If you're having on this script or the ansible roles to change the
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

    $ vagrant destroy

Any PXE client VMs you created will need to be removed by hand.

## Running the web UI

We are experimenting with single page web UI applications within the repository
`on-web-ui` (https://github.com/rackhd/on-web-ui). That repository includes a
README and is set up to host the UI externally to the RackHD. Follow the
README instructions in that repository to run the application, and you can
change the settings while running to point to this instance of RackHD at
`https://localhost:9090/`
