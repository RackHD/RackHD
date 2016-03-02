FROM alpine:latest

RUN apk add --update dhcp

RUN rm -rf /var/lib/dhcp && \
    mkdir -p /var/lib/dhcp && \
    chown -R root:root /var/lib/dhcp && \
    chmod 766 /var/lib/dhcp && \
    touch /var/lib/dhcp/dhcpd.leases && \
    chown root:root /var/lib/dhcp/dhcpd.leases && \
    chmod 666 /var/lib/dhcp/dhcpd.leases

VOLUME /var/lib/dhcp

VOLUME /etc/dhcp
VOLUME /etc/defaults

EXPOSE 67/udp

COPY ./docker-entrypoint.sh /docker-entrypoint.sh

CMD [ "/docker-entrypoint.sh" ]
