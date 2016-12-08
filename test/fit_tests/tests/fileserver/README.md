# External File Server(On-static) Test:

This test validate the function of RackHD On-static file server. You need put an config file in the /config directory containing the test file url. The test date should write in jon format and save as fileserver_config.jon. The following is an example.
The first part contains external OS image repos, the second part contains microkernel image repos, the third party is the credential of fileserver used for testing local iso mount.

Sample global_config.json file:

    {"os_image":
    [{"osname":"esxi",
      "version":"6.0" ,
      "linktype":"http",
      "url":"http://10.62.59.209/static/images/VMware-VMvisor-Installer-6.0.0-2494585.x86_64.iso"
            },
    {"osname":"openSUSE",
      "version":"42.1" ,
      "linktype":"ftp",
      "url":"ftp://10.62.59.23/os/images/openSUSE-Leap-42.1-DVD-x86_64.iso"
            },
      {"osname":"Ubuntu",
      "version":"16.04" ,
      "linktype":"http",
      "url":"http://10.62.59.209/static/images/ubuntu-16.04-server-amd64.iso"
            },
      {"osname":"CentOS",
      "version":"7.0" ,
      "linktype":"ftp",
      "url":"ftp://10.62.59.23/os/images/CentOS-7.0-1406-x86_64-DVD.iso"
            },
       {"osname":"Ubuntuserver",
      "version":"14.04" ,
      "linktype":"ftp",
      "url":"ftp://10.62.59.23/os/images/ubuntu-14.04.2-server-amd64.iso"
            }
      ],
    "microkernel":["http://web.hwimo.lab.emc.com/autotest/staticfile/vmlinuz-3.16.0-25-generic",
                   "http://web.hwimo.lab.emc.com/autotest/staticfile/discovery.overlay.cpio.gz",
                   "http://web.hwimo.lab.emc.com/autotest/staticfile/initrd.img-3.16.0-25-generic",
                   "http://web.hwimo.lab.emc.com/autotest/staticfile/base.trusty.3.16.0-25-generic.squashfs.img"],
    "usr":"onrack",
    "pwd":"onrack"

}

