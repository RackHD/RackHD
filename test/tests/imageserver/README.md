# Image service Test:

This test validate the function of RackHD image service. There are 3 parts of test:
###1. Test OS image service
This test OS image operation related APIs of image-service.
###2. Test microkernel service
This test microkernel management related APIs of image-service
###3. Test bootstraping and rediscovery
This test RackHD and image service working together to do OS bootstrapping and node rediscovery.

##Config file
You need put an config file in the /config directory containing the test file url. The test date should write in json format and save as fileserver_config.jon. The following is an example.
The first part contains external OS image repos, the second part contains microkernel image repos, the third part is the credential of fileserver used for testing local iso mount.
When start FIT test, you need add "-extra imageservice_config.json" parameter to load this config file.
###filetocompare
This is the parameter to specify the max file to go through in each repo. Some iso repo may have thousands of files. It unnecessary to go though all of them. 


##FIT parameter
An optional FIT parameter "-imageserver" is used to specify the image service server IP(management port). It can override the parameter with the same name in imageservice_config.json. Use as "-imageserver=xx.xx.xx.xx"

##Example 
python run_tests.py -test ./tests/fileserver/test_os_static_file_server.py  -rackhd_host XX.XX.XX.XX -extra imageservice_config.json -imageserver=xx.xx.xx.xx

Sample global_config.json file:
 {
  "image_service": {
    "os_image": [
      {
        "osname": "ESXi",
        "version": "6.0",
        "linktype": "http",
        "url": "http://10.240.19.193/repo/ISO/VMware-VMvisor-Installer-6.0.0.update02-3620759.x86_64.iso"
      },
      {
        "osname": "Ubuntu",
        "version": "16.04",
        "linktype": "http",
        "url": "http://10.240.19.193/repo/ISO/ubuntu-14.04.4-server-amd64.iso"
      },
      {
        "osname": "CentOS",
        "version": "7.0",
        "linktype": "http",
        "url": "http://10.240.19.193/repo/ISO/CentOS-7-x86_64-DVD-1511.iso"
      },
      {
        "osname": "Ubuntuserver",
        "version": "14.04",
        "linktype": "http",
        "url": "http://10.240.19.193/repo/ISO/ubuntu-14.04.4-server-amd64.iso"
      },
      {
        "osname": "RedhatEnterpise",
        "version": "7.2",
        "linktype": "http",
        "url": "http://10.240.19.193/repo/ISO/rhel-server-7.2-x86_64-dvd.iso"
      },
      {
        "osname": "openSUSE",
        "version": "42.1",
        "linktype": "http",
        "url": "http://10.240.19.193/repo/ISO/openSUSE-Leap-42.1-DVD-x86_64.iso"
      }
    ],
    "microkernel": [
      "scp:///var/renasar/on-http/static/http/common/vmlinuz-3.16.0-25-generic",
      "scp:///var/renasar/on-http/static/http/common/discovery.overlay.cpio.gz",
      "scp:///var/renasar/on-http/static/http/common/initrd.img-3.16.0-25-generic",
      "scp:///var/renasar/on-http/static/http/common/base.trusty.3.16.0-25-generic.squashfs.img"
    ],
    "usr": "onrack",
    "pwd": "onrack",
    "imageserver":"localhost",
    "control_port":7070,
    "file_port":9090,
    "filetocompare": 100
  }
}

