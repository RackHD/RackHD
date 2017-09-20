FROM ubuntu:latest


#Install Docker-CE
RUN apt-get update
#RUN  apt-get install -y \
#     linux-image-extra-$(uname -r) \
#     linux-image-extra-virtual

RUN apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common

RUN  curl -fsSL https://download.docker.com/linux/ubuntu/gpg |  apt-key add -
RUN  apt-key fingerprint 0EBFCD88
RUN  add-apt-repository \
      "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) \
      stable"

RUN apt-get update \
&&  apt-get install -y docker-ce

#install docker-compose
RUN curl -L https://github.com/docker/compose/releases/download/1.16.1/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose




#Install InfraSIM
RUN  apt-get update \
&&   apt-get install -y bridge-utils \
&&   apt-get install -y libnuma-dev \
&&   apt-get install -y libaio1 libaio-dev \
&&   apt-get install -y python-pip libpython-dev libssl-dev \
&&   pip install --upgrade pip \
&&   pip install setuptools  \
&&   pip install infrasim-compute

RUN pip install virtualenv

# install git
RUN  apt-get install -y git

# config InfraSIM
RUN infrasim init
COPY infrasim_config.yml  /root/.infrasim/.node_map/default.yml
RUN infrasim node destroy

RUN apt-get install -y net-tools wget

COPY ./docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# remove apt caches
RUN rm -rf /var/lib/apt/lists/*


EXPOSE 27017 5672 15672 67/udp 9080 9090 8443 69/udp 514/udp 68/udp 4011

ENTRYPOINT [ "/docker-entrypoint.sh" ]
