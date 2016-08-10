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
  * docker v1.10 or higher
  * docker-compose v1.6 or higher [Install Docker Compose](https://docs.docker.com/compose/install/)

```
$ cd RackHD/docker
$ sudo docker-compose pull         # Download prebuilt docker images.
$ sudo docker-compose up           # Create containers and Run RackHD and ELK.
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

## Using Docker on the EMC network:
If you're trying to run this example inside the EMC see:
https://github.com/emccode/training/tree/master/docker-workshops/docker-platform-intro/lab1-your-first-container#for-emc-employees-only

## Discovering a VirtualBox VM in RackHD.

This example is meant to run on Mac OS X or if you're using VirtualBox to run RackHD on Docker.

```
$ NAME=pxe-1 ./create_pxe_vm.bash   # Creates PXE VM in VirtualBox.
```

Now start `pxe-1` from VirtualBox. You should see it boot and auto automatically get discovered and catalogs by RackHD.

If the VM boots and is not discovered make sure you used './docker_vm_up.bash' to setup your `boot2docker.iso` VM. Otherwise it will not discover your PXE VM.

## Troubleshoot common Vagrant issues.
  If running `./docker_vm_up.bash` fails:
    * By default the b2d vagrant vm exposes all related ports. Some of which are only necessary for development and debugging. You can disable any ports you do not wish to use, or change the which port on the host they map too.
    * Ensure you have the right version of Vagrant for VirtualBox. Later versions of VirtualBox require a more recent version of Vagrant.

## Run a minimal set of RackHD containers (without ELK).
For who doesn't need ELK running along with RackHD, due to system performance restriction or docker-pull network bandwidth restriction: an alternative docker-compose file can be used by "-f" option:

```
$ docker-compose -f docker-compose-mini.yml pull
$ docker-compose -f docker-compose-mini.yml up
```




## Running this example without `docker-compose`.

For convenience there are alternative scripts you can use instead of `docker-compose`.

```
$ ./scripts/compose_services.bash    # Run all RackHD/ELK docker containers.
$ ./scripts/follow_services.bash     # Follow all RackHD/ELK logs.
$ ./scripts/restart_services.bash    # Restart all RackHD/ELK docker containers.
$ ./scripts/stop_services.bash       # Stop all RackHD/ELK docker containers.
$ ./scripts/remove_services.bash     # Remove all RackHD/ELK docker containers
```
