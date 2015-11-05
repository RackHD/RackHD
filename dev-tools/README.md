#Documentation...

## PRE-REQS

  We expect the latest version of GIT, Vagrant, and Ansible installed onto the host system.

  We expect static files to be located in the correct path from the parent directory of dev-tools:

    i.e.
        ~/<repos directory>/RackHD/on-http/static/http/common/



## SET UP INSTRUCTIONS


  Clone RackHD repo to your local git directory.

    i.e.
        ~/<repos directory>/RackHD/


  Within the dev-tools directory, create config and run the setup command:

    $ cd ~/<repos directory>/RackHD/dev-tools/config/

    $ cp ./monorail_rack.cfg.example ./monorail_rack.cfg

    Edits can be made to this new file to adjust the number of clients created.


    $ cd ~/<repos directory>/RackHD/dev-tools/bin/

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


## TESTING

  Test node was discovered from the monorail server:

    $ curl localhost:8080/api/1.1/nodes | python -m json.tool

  Check Cataloging has happend:

    $ mongo pxe --eval 'db.catalogs.count()'
