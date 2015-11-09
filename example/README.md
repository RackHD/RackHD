## DOCUMENTATION

  The monorail_rack setup script is an easy "one button push" script to deploy an virtual rack within virtualbox to emulate a monorail server and some number of virtualbox PXE-booting clients. The enviornment is tied together using a virtual network called closednet set to our defualt subnet of 172.31.128.x for servicing DHCP and TFTP to the PXE clients.

## PRE-REQS

  We expect the latest version of GIT, Vagrant, and Ansible installed onto the host system.

  We expect static files to be located in the correct path from the parent directory of dev-tools:

    i.e.
        ~/<repos directory>/RackHD/on-http/static/http/common/

  Our static files can be built locally using the tools found here:
      https://github.com/RackHD/on-imagebuilder

## SET UP INSTRUCTIONS


  Clone RackHD repo to your local git directory.

    i.e.
        ~/<repos directory>/RackHD/


  Within the example directory, create config and run the setup command:

    $ cd ~/<repos directory>/RackHD/example/config/

    $ cp ./monorail_rack.cfg.example ./monorail_rack.cfg

    Edits can be made to this new file to adjust the number of pxe clients created.
    Please see below for more information on the configuration file.

    $ cd ~/<repos directory>/RackHD/example/bin/

    $ ./monorail_rack

  Copy local basic static files to common directory:

    $ cp ~/<static files directory>/* ~/<repos directory>/RackHD/on-http/static/http/common/

  Now ssh into the monorail server:

    $ vagrant ssh dev

  Bring up all monorail services:

    $ sudo nf start
      or $ sudo nf start [graph,http,dhcp,tftp,syslog]

    Now that the services are running we can begin powering on pxe clients and watch them boot.


  Provision an existing monorail server:

    $ vagrant provision

## CONFIGURATION FILE

```
# monorail_rack.cfg
# used to customize default deployment
# edit $pxe_count to change the amount of virtualbox PXE-booting clients are created when running
# the monorail_rack setup script.

# deployment variables
pxe_count=1
```

Changing the number of $pxe_count within the running configuration script will effect how many headless pxe clients are created when running the monorail_rack setup script.

Please note, and example configuration file is provided and you must copy that file to a new file with the same name excluding the .example extension.


## ENVIRONMENT BREAKDOWN

  Remove an existing monorail server:

    $ vagrant destroy

  Please note all pxe clients must to be removed by hand currently.


## CHANGE NODE VERSION

  Currently the monorail server is built with Node v0.10.40 but this can be changed.

  Install additional Node versions

    $ sudo ~/n/bin/n <version>

  Use n's menu system to change running Node version

    $ sudo ~/n/bin/n

## CHANGE CODE VERSION USED

  To checkout to a different commit than what is referenced by git submodule, edit the vagrant file (RackHD/example/Vagrantfile) to specify the branch variable for the ansible provisioner.

```
    # If you wish to use a specific commit, include the variable below.
    ansible.extra_vars = { branch: "master" }
```

## TESTING

  Test node was discovered from the monorail server:

    $ curl localhost:8080/api/1.1/nodes | python -m json.tool

  Check Cataloging has happend:

    $ mongo pxe --eval 'db.catalogs.count()'
