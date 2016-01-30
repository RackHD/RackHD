# RackHD on Docker instructions

Install Docker Toolbox on your system. See https://www.docker.com/products/docker-toolbox

This has only been tested on Mac OS X.

```
$ cd RackHD/docker
$ ./checkout_submodules.bash  # Checkout submodule Docker branches
$ vagrant up b2d              # Spin up custom boot2docker vm
$ . export_docker_host.bash   # Point docker host to b2d vm
$ ./build_images.bash         # Build RackHD Docker images
$ docker-compose up           # Run RackHD on Docker with ELK
```

Exposed Services:
* http://127.0.0.1:15672/ - RabbitMQ Managment
* http://127.0.0.1:5601/ - Kibana
* http://127.0.0.1:9090/docs - RackHD Docs
* http://127.0.0.1:9090/ui - RackHD UI
* http://127.0.0.1:9200/ - Elasticsearch
