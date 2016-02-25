# Using Docker to run RackHD along with ELK.

Copyright 2016, EMC, Inc.

## On Mac OS X.

**Prerequisites:**
  * Install Vagrant. See https://www.vagrantup.com/docs/installation/
  * Install Docker Toolbox. See https://www.docker.com/products/docker-toolbox

```
$ cd RackHD/docker
$ ./docker_vm_up.bash         # Spin up boot2docker.iso vagrant box.
$ . export_docker_host.bash   # Point docker host to b2d vm.
$ docker-compose up           # Run RackHD and ELK.
```

## On a Linux host.


**Prerequisites:**
  * docker v1.10
  * docker-compose v1.6

```
$ cd RackHD/docker
$ docker-compose pull         # Download prebuilt docker images.
$ docker-compose start        # Run RackHD and ELK.
```

## Once RackHD and ELK are running.

Open http://127.0.0.1:9090 in a web browser.

The `index.html` file being service is located at: `RackHD/docker/monorail/static/http`.

You can actually edit this file and refresh your browser to see your changes.

## How to change RackHD config.

Simply edit the `RackHD/docker/monorail/config.json` file and restart your containers.

```
docker-compose restart        # Restart RackHD and ELK.
```

## Rebuild RackHD images for development.

It is recommended that you uncomment the `core` RackHD service before developing RackHD. This service doesn't need to run but it should be rebuilt before other RackHD images are built.

```
$ ../scripts/reset_submodules.bash  # Fetch latest submodules.
$ docker-compose build              # Build RackHD Docker images.
$ docker-compose kill               # Force stop running RackHD/ELK containers.
$ docker-compose rm -f              # Remove previous RackHD/ELK containers.
$ docker-compose create             # Create new RackHD/ELK containers.
$ docker-compose start              # Run RackHD and ELK.
$ docker-compose logs               # Show docker logs.
```

## DHCP Server runs by default.

By default this will run `dhcpd` on `eth1`, however you can change the configuration at `RackHD/docker/dhcp/config/dhcpd.conf` and `RackHD/docker/dhcp/defaults/isc-dhcp-server`.

Restart `rackhd/isc-dhcp-server` and the changes will take effect.

The `dhcpd.leases` file is shared between docker containers using a docker volume.

You can disable the DHCP server by commenting it out the `docker-compose.yml` file.

Or after you've started all containers you can run:

```
$ docker-compose kill dhcp    # Stop the DHCP server.
```

## Shared on-http and on-tftp files.

The `rackhd/files` image shares `on-http` and `on-tftp` file downloads with the host machine. **Experimental**

## Using docker on the EMC network:
https://github.com/emccode/training/tree/master/docker-workshops/docker-platform-intro/lab1-your-first-container#for-emc-employees-only
