FROM alpine:latest

RUN mkdir -p /RackHD/downloads

ADD https://bintray.com/artifact/download/rackhd/binary/ipxe/monorail-efi32-snponly.efi \
    /RackHD/downloads/monorail-efi32-snponly.efi
ADD https://bintray.com/artifact/download/rackhd/binary/ipxe/monorail-efi64-snponly.efi \
    /RackHD/downloads/monorail-efi64-snponly.efi
ADD https://bintray.com/artifact/download/rackhd/binary/ipxe/monorail.ipxe \
    /RackHD/downloads/monorail.ipxe
ADD https://bintray.com/artifact/download/rackhd/binary/ipxe/monorail-undionly.kpxe \
    /RackHD/downloads/monorail-undionly.kpxe
ADD https://bintray.com/artifact/download/rackhd/binary/ipxe/monorail.intel.ipxe \
    /RackHD/downloads/monorail.intel.ipxe

ADD https://bintray.com/artifact/download/rackhd/binary/syslinux/undionly.kkpxe \
    /RackHD/downloads/undionly.kkpxe


RUN mkdir -p /RackHD/downloads/common

ADD https://bintray.com/artifact/download/rackhd/binary/builds/base.trusty.3.16.0-25-generic.squashfs.img \
    /RackHD/downloads/common/base.trusty.3.16.0-25-generic.squashfs.img
ADD https://bintray.com/artifact/download/rackhd/binary/builds/discovery.overlay.cpio.gz \
    /RackHD/downloads/common/discovery.overlay.cpio.gz
ADD https://bintray.com/artifact/download/rackhd/binary/builds/initrd.img-3.16.0-25-generic \
    /RackHD/downloads/common/initrd.img-3.16.0-25-generic
ADD https://bintray.com/artifact/download/rackhd/binary/builds/vmlinuz-3.16.0-25-generic \
    /RackHD/downloads/common/vmlinuz-3.16.0-25-generic

VOLUME /RackHD/files

COPY ./docker-entrypoint.sh /docker-entrypoint.sh

CMD [ "/docker-entrypoint.sh" ]
