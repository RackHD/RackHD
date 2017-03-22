# External File Server(On-static) Test:

This test validate the function of RackHD image service. There are 3 parts of test:
###1. Test OS image service
This test OS image operation related APIs of image-service.
###2. Test microkernel service
This test microkernel management related APIs of image-service
###3. Test 
This test RackHD+ image service working together to do OS bootstrapping and node rediscovery.

##Config file
You need put an config file in the /config directory containing the test file url. The test date should write in json format and save as fileserver_config.jon. The following is an example.
The first part contains external OS image repos, the second part contains microkernel image repos, the third part is the credential of fileserver used for testing local iso mount.
When test the fileserver, you need set a environment variable $IMAGESERVER first, then you can run the FIT test. It is need to specify the fileserver's credential by "usr" and "pwd" and "supwd" is the test server's admin user's password
###filetocompare
This is the parameter to specify the max file to go through in each repo. Some iso repo may have thousands of files. It unnecessary to go though all of them. 
###rackhd_control_ip
This parameter is the south bound nic ip of RackHD. It is 172.31.128.1 be default.

##FIT parameter
-imageserver is used to specify the image service server IP. Use as "-imageserver=xx.xx.xx.xx"

##Example 
python run_tests.py -test ./tests/fileserver/test_os_static_file_server.py  -rackhd_host XX.XX.XX.XX  -imageserver=xx.xx.xx.xx

Sample global_config.json file:

    {"os_image":[
      {"osname":"Ubuntu",
      "version":"16.04" ,
      "linktype":"http",
      "url":"http://10.240.19.193/repo/ISO/ubuntu-14.04.4-server-amd64.iso"
            },
      {"osname":"CentOS",
      "version":"7.0" ,
      "linktype":"http",
      "url":"http://10.240.19.193/repo/ISO/CentOS-7-x86_64-DVD-1511.iso"
            },
       {"osname":"Ubuntuserver",
      "version":"14.04" ,
      "linktype":"http",
      "url":"http://10.240.19.193/repo/ISO/ubuntu-14.04.4-server-amd64.iso"
            }
      ],
    "microkernel":["http://web.hwimo.lab.emc.com/autotest/staticfile/vmlinuz-3.16.0-25-generic",
                   "http://web.hwimo.lab.emc.com/autotest/staticfile/discovery.overlay.cpio.gz",
                   "http://web.hwimo.lab.emc.com/autotest/staticfile/initrd.img-3.16.0-25-generic",
                   "http://web.hwimo.lab.emc.com/autotest/staticfile/base.trusty.3.16.0-25-generic.squashfs.img"],
    "usr":"onrack",
    "pwd":"onrack"
    "filetocompare":100,
    "rackhd_control_ip":"172.31.128.1"
}

