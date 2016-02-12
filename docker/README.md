# RackHD on Docker instructions.

Copyright 2016, EMC, Inc.

**Prerequisites:**
  * Install Vagrant on your system. See https://www.vagrantup.com/docs/installation/
    NOTE: Make sure you install version 1.9.1 -- https://github.com/docker/toolbox/releases/tag/v1.9.1j
  * Install Docker Toolbox on your system. See https://www.docker.com/products/docker-toolbox

```
$ cd RackHD/docker
$ vagrant up b2d              # Spin up custom boot2docker vm.
$ . export_docker_host.bash   # Point docker host to b2d vm.
$ docker-compose up           # Run RackHD on Docker with ELK.
```

Exposed Services:
* http://127.0.0.1:15672/ - RabbitMQ Managment
* http://127.0.0.1:5601/ - Kibana
* http://127.0.0.1:9090/docs - RackHD Docs
* http://127.0.0.1:9090/ui - RackHD UI
* http://127.0.0.1:9200/ - Elasticsearch

## Running on Linux host with Docker.

Make sure you clone the RackHD repo to the system root: `/RackHD`. Or create a symbolic link.

This is required because the volumes in the `docker-compose.yml` assume that RackHD is located at the root. The reason for this is to allow the mounts to work within a vagrant VM. If you look at the `docker/Vagrantfile` you'll see the RackHD repo is shared a shared directory.

No need to have vagrant installed unless you want to run the RackHD docker containers in a VM on Linux.

Both `docker` and `docker-compose` are still required.

```
$ cd /RackHD/docker
$ docker-compose start
```

Warning: This will run `dhcpd` on `eth1`, however you can change the configuration at `/RackHD/docker/dhcp/config/dhcpd.conf` and `/RackHD/docker/dhcp/defaults/isc-dhcp-server`. Restart `rackhd/on-taskgraph` and the changes will take effect.

Avoid binding to any of the ports RackHD or ELK uses:
  * 67
  * 68
  * 69
  * 514
  * 4011
  * 5000
  * 5601
  * 5672
  * 8080
  * 8090
  * 8125
  * 9200
  * 9300
  * 15672
  * 25672
  * 27017

## Rebuilding images for development.

```
$ ../scripts/reset_submodules.bash  # Fetch latest submodules.
$ ./build_images.bash               # Build RackHD Docker images.
$ docker-compose restart            # Restart RackHD containers.
```

#### Using docker on the EMC network:
https://github.com/emccode/training/tree/master/docker-workshops/docker-platform-intro/lab1-your-first-container#for-emc-employees-only
