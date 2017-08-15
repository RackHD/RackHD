# Build and Run RackHD demo

1. clone and build RackHD code into a local folder (named build-deps).(e.x. using RackHD/example/install_rackhd.sh )
2. move the build-deps into this folder
3. Build a new docker images with the RackHD code in build-deps folder
    docker build -t $name_of_image .
4. Run this docker images with privileged mode
    docker run -idt --rm --name=demo  --privileged  $name_of_image  /bin/bash
5. Watch the logs. it will start RackHD, start an InfraSIM then run FIT smoke-test .
   docker logs demo --follow


