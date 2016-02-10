FROM alpine:latest

RUN apk add --update dhcp

EXPOSE 67/udp

VOLUME /var/lib/dhcp

COPY ./docker-entrypoint.sh /docker-entrypoint.sh

CMD [ "/docker-entrypoint.sh" ]
