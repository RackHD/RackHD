# RackHD on Docker instructions

Install Docker on your system. See https://www.docker.com/

```
$ cd RackHD/docker
$ vagrant up b2d
$ . export_docker_host.bash
$ ./build-images.bash
$ docker-compose up
```

This has only been tested on Mac OS X.
