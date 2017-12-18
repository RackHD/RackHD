FROM rackhd/pipeline:latest

#Install InfraSIM
RUN  apt-get update \
&&   apt-get install -y bridge-utils \ 
&&   apt-get install -y libnuma-dev \ 
&&   apt-get install -y python-pip libpython-dev libssl-dev \
&&   sudo pip install --upgrade pip \
&&   sudo pip install setuptools  \
&&   sudo pip install infrasim-compute

RUN pip install virtualenv

RUN mkdir /RackHD
RUN mkdir -p /opt/monorail
COPY ./build-deps /RackHD/
COPY ./monorail /opt/monorail
COPY rackhd.yml /


# config InfraSIM
RUN sudo infrasim init
COPY infrasim_config.yml  /root/.infrasim/.node_map/default.yml
RUN sudo infrasim node destroy



COPY ./docker-entrypoint.sh /docker-entrypoint.sh


EXPOSE 27017 5672 15672 67/udp 9080 9090 8443 69/udp 514/udp 68/udp 4011

ENTRYPOINT [ "/docker-entrypoint.sh" ]
