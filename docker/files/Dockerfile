FROM wheezy:latest

RUN echo "deb https://dl.bintray.com/rackhd/debian trusty release" >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get install on-imagebuilder

RUN mkdir -p /RackHD/downloads
COPY /var/renasar/on-tftp/static/tftp/* /RackHD/downloads

RUN mkdir -p /RackHD/downloads/common
COPY /var/renasar/on-http/static/http/common/* /RackHD/downloads/common

VOLUME /RackHD/files

COPY ./docker-entrypoint.sh /docker-entrypoint.sh

CMD [ "/docker-entrypoint.sh" ]
