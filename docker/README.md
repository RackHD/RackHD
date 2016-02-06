# RackHD on Docker instructions

Copyright 2016, EMC, Inc.

Install Docker Toolbox on your system. See https://www.docker.com/products/docker-toolbox

This has only been tested on Mac OS X.

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

## Rebuilding images for development

```
$ ../scripts/reset_submodules.bash  # Fetch latest submodules.
$ ./build_images.bash               # Build RackHD Docker images.
$ docker-compose restart            # Restart RackHD containers.
```

#### Using docker on the EMC network:
https://github.com/emccode/training/tree/master/docker-workshops/docker-platform-intro/lab1-your-first-container#for-emc-employees-only
