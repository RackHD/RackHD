# Copyright 2016, EMC, Inc.

FROM frolvlad/alpine-python2:latest

RUN apk add --update build-base gcc abuild binutils python-dev py-pip libffi-dev openssl-dev \
  && pip install --upgrade pip

COPY . /RackHD/test/
WORKDIR /RackHD/test

RUN cd /RackHD/test \
  && pip install -r requirements.txt

ENV RACKHD_TEST_LOGLVL ${RACKHD_TEST_LOGLVL:-DEBUG}
ENV RACKHD_HOST ${RACKHD_HOST:-127.0.0.1}
ENV RACKHD_PORT ${RACKHD_PORT:-9090}
ENV RACKHD_AMQP_URL ${RACKHD_AMQP_URL:-amqp://127.0.0.1:5672}

CMD [ "python", "/RackHD/test/run.py" ]
