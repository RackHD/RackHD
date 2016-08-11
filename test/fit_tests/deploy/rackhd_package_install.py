'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

This script installs RackHD from BinTray packages onto blank OS.
'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common

# local methods
ENVVARS = ''
if 'proxy' in fit_common.GLOBAL_CONFIG['repos'] and fit_common.GLOBAL_CONFIG['repos']['proxy'] != '':
    ENVVARS = "export http_proxy=" + fit_common.GLOBAL_CONFIG['repos']['proxy'] + ";" + \
              "export https_proxy=" + fit_common.GLOBAL_CONFIG['repos']['proxy'] + ";"

class rackhd_package_install(fit_common.unittest.TestCase):
    def test01_install_rackhd_dependencies(self):
        print "**** Installing RackHD dependencies."
        # install dependencies
        self.assertEqual(fit_common.remote_shell("apt-get -y install rabbitmq-server")['exitcode'], 0, "rabbitmq-server Install failure.")
        self.assertEqual(fit_common.remote_shell("apt-get -y install mongodb")['exitcode'], 0, "mongodb Install failure.")
        self.assertEqual(fit_common.remote_shell("apt-get -y install snmp")['exitcode'], 0, "snmp Install failure.")
        self.assertEqual(fit_common.remote_shell("apt-get -y install ipmitool")['exitcode'], 0, "ipmitool Install failure.")
        # install Node
        fit_common.remote_shell('apt-get -y remove nodejs nodejs-legacy')
        fit_common.remote_shell(ENVVARS +
                                'wget --quiet -O - https://deb.nodesource.com/gpgkey/nodesource.gpg.key | sudo apt-key add -;'
                                'echo "deb https://deb.nodesource.com/node_4.x trusty main" | tee /etc/apt/sources.list.d/nodesource.list;'
                                'echo "deb-src https://deb.nodesource.com/node_4.x trusty main" | tee -a /etc/apt/sources.list.d/nodesource.list;')
        fit_common.remote_shell('apt-get -y update;'
                                'apt-get -y install nodejs;'
                                )
        fit_common.remote_shell('apt-get -y install npm;npm config set https-proxy '
                                + fit_common.GLOBAL_CONFIG['repos']['proxy'])
        # Install Ansible
        self.assertEqual(fit_common.remote_shell("apt-get -y install ansible")['exitcode'], 0, "ansible Install failure.")
        self.assertEqual(fit_common.remote_shell("apt-get -y install apt-mirror")['exitcode'], 0, "apt-mirror Install failure.")
        self.assertEqual(fit_common.remote_shell("apt-get -y install amtterm")['exitcode'], 0, "amtterm Install failure.")
        self.assertEqual(fit_common.remote_shell("apt-get -y install isc-dhcp-server")['exitcode'], 0, "isc-dhcp-server Install failure.")
        # collect nic names
        iflist = fit_common.remote_shell("ifconfig -s -a | tail -n +2 | awk \\\'{print \\\$1}\\\' |grep -v lo")['stdout'].split()
        # install network config
        self.assertEqual(fit_common.remote_shell("echo 'auto " + iflist[7] + "' > /etc/network/interfaces.d/control.cfg;"
                                                  "echo 'iface " + iflist[7] + " inet static' >> /etc/network/interfaces.d/control.cfg;"
                                                  "echo 'address 172.31.128.1' >> /etc/network/interfaces.d/control.cfg;"
                                                  "echo 'netmask 255.255.252.0' >> /etc/network/interfaces.d/control.cfg"
                                                  )['exitcode'], 0, "Network config failure.")
        self.assertEqual(fit_common.remote_shell("echo 'auto " + iflist[8] + "' > /etc/network/interfaces.d/pdudirect.cfg;"
                                                  "echo 'iface " + iflist[8] + " inet static' >> /etc/network/interfaces.d/pdudirect.cfg;"
                                                  "echo 'address 192.168.1.1' >> /etc/network/interfaces.d/pdudirect.cfg;"
                                                  "echo 'netmask 255.255.255.0' >> /etc/network/interfaces.d/pdudirect.cfg"
                                                  )['exitcode'], 0, "Network config failure.")

    def test02_install_rackhd_packages(self):
        print "**** Installing RackHD packages."
        self.assertEqual(fit_common.remote_shell("echo 'deb https://dl.bintray.com/rackhd/debian trusty main' | tee -a /etc/apt/sources.list")['exitcode'], 0, "Package Install failure.")
        self.assertEqual(fit_common.remote_shell(ENVVARS
                                                  + "apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 379CE192D401AB61")['exitcode'], 0, "Package Install failure.")
        self.assertEqual(fit_common.remote_shell(ENVVARS
                                                  + "apt-get -y update")['exitcode'], 0, "Install failure.")
        self.assertEqual(fit_common.remote_shell(ENVVARS
                                                  + "apt-get -y install on-dhcp-proxy on-http on-taskgraph")['exitcode'], 0, "Package Install failure.")
        self.assertEqual(fit_common.remote_shell(ENVVARS
                                                  + "apt-get -y install on-tftp on-syslog")['exitcode'], 0, "Package Install failure.")

    def test03_install_rackhd_config_files(self):
        print "**** Installing RackHD config files."
        #create DHCP config
        dhcp_conf = open("dhcpd.conf", 'w')
        dhcp_conf.write(
                        'ddns-update-style none;\n'
                        'option domain-name "example.org";\n'
                        'option domain-name-servers ns1.example.org, ns2.example.org;\n'
                        'default-lease-time 600;\n'
                        'max-lease-time 7200;\n'
                        'log-facility local7;\n'
                        'deny duplicates;\n'
                        'ignore-client-uids true;\n'
                        'subnet 172.31.128.0 netmask 255.255.252.0 {\n'
                        '  range 172.31.128.2 172.31.131.254;\n'
                        '  option vendor-class-identifier "PXEClient";\n'
                        '}\n'
                         )
        dhcp_conf.close()
        # create RackHD config
        hdconfig = {
                    "CIDRNet": "172.31.128.0/22",
                    "amqp": "amqp://localhost",
                    "apiServerAddress": "172.31.128.1",
                    "apiServerPort": 9080,
                    "broadcastaddr": "172.31.131.255",
                    "dhcpGateway": "172.31.128.1",
                    "dhcpProxyBindAddress": "172.31.128.1",
                    "dhcpProxyBindPort": 4011,
                    "dhcpSubnetMask": "255.255.252.0",
                    "gatewayaddr": "172.31.128.1",
                    "httpEndpoints": [
                        {
                            "address": "0.0.0.0",
                            "port": fit_common.GLOBAL_CONFIG['ports']['http'],
                            "httpsEnabled": False,
                            "proxiesEnabled": True,
                            "authEnabled": False,
                            "routers": "northbound-api-router"
                        },
                        {
                            "address": "0.0.0.0",
                            "port": fit_common.GLOBAL_CONFIG['ports']['https'],
                            "httpsEnabled": True,
                            "proxiesEnabled": True,
                            "authEnabled": True,
                            "routers": "northbound-api-router"
                        },
                        {
                            "address": "172.31.128.1",
                            "port": 9080,
                            "httpsEnabled": False,
                            "proxiesEnabled": True,
                            "authEnabled": False,
                            "routers": "southbound-api-router"
                        }
                    ],
                    "httpDocsRoot": "./build/apidoc",
                    "httpFileServiceRoot": "./static/files",
                    "httpFileServiceType": "FileSystem",
                    "httpProxies": [{
                        "localPath": "/mirror",
                        "remotePath": "/",
                        "server": fit_common.GLOBAL_CONFIG['repos']['mirror']
                    }],
                    "httpStaticRoot": "/opt/monorail/static/http",
                    "minLogLevel": 3,
                    "authUsername": "admin",
                    "authPasswordHash": "KcBN9YobNV0wdux8h0fKNqi4uoKCgGl/j8c6YGlG7iA0PB3P9ojbmANGhDlcSBE0iOTIsYsGbtSsbqP4wvsVcw==",
                    "authPasswordSalt": "zlxkgxjvcFwm0M8sWaGojh25qNYO8tuNWUMN4xKPH93PidwkCAvaX2JItLA3p7BSCWIzkw4GwWuezoMvKf3UXg==",
                    "authTokenSecret": "RackHDRocks!",
                    "authTokenExpireIn": 86400,
                    "mongo": "mongodb://localhost/pxe",
                    "sharedKey": "qxfO2D3tIJsZACu7UA6Fbw0avowo8r79ALzn+WeuC8M=",
                    "statsd": "127.0.0.1:8125",
                    "subnetmask": "255.255.252.0",
                    "syslogBindAddress": "172.31.128.1",
                    "syslogBindPort": 514,
                    "tftpBindAddress": "172.31.128.1",
                    "tftpBindPort": 69,
                    "tftpRoot": "./static/tftp",
                    "minLogLevel": 2
                }
        config_json = open("config.json", 'w')
        config_json.write(fit_common.json.dumps(hdconfig, sort_keys=True, indent=4))
        config_json.close()
        # copy files to ORA
        fit_common.scp_file_to_ora("config.json")
        fit_common.scp_file_to_ora("dhcpd.conf")
        self.assertEqual(fit_common.remote_shell('cp dhcpd.conf /etc/dhcp/')['exitcode'], 0, "DHCP Config failure.")
        self.assertEqual(fit_common.remote_shell('cp config.json /opt/monorail/')['exitcode'], 0, "RackHD Config file failure.")
        os.remove('dhcpd.conf')
        os.remove('config.json')

    def test04_install_rackhd_binary_support_packages(self):
        print "**** Installing RackHD binaries."
        self.assertEqual(fit_common.remote_shell(
            ENVVARS +
            "mkdir -p /var/renasar/on-tftp/static/tftp;"
            "cd /var/renasar/on-tftp/static/tftp;"
            "wget 'https://dl.bintray.com/rackhd/binary/ipxe/undionly.kpxe';"
            "wget 'https://dl.bintray.com/rackhd/binary/ipxe/monorail-undionly.kpxe';"
            "wget 'https://dl.bintray.com/rackhd/binary/ipxe/monorail-efi64-snponly.efi';"
            "wget 'https://dl.bintray.com/rackhd/binary/ipxe/monorail-efi32-snponly.efi';"
        )['exitcode'], 0, "Binary Support Install failure.")
        self.assertEqual(fit_common.remote_shell(
            ENVVARS +
            "mkdir -p /var/renasar/on-http/static/http/common;"
            "cd /var/renasar/on-http/static/http/common;"
            "wget 'https://dl.bintray.com/rackhd/binary/builds/base.trusty.3.16.0-25-generic.squashfs.img';"
            "wget 'https://dl.bintray.com/rackhd/binary/builds/discovery.overlay.cpio.gz';"
            "wget 'https://dl.bintray.com/rackhd/binary/builds/initrd.img-3.16.0-25-generic';"
            "wget 'https://dl.bintray.com/rackhd/binary/builds/vmlinuz-3.16.0-25-generic';"
        )['exitcode'], 0, "Binary Support Install failure.")

    def test05_reboot_and_check(self):
        print "**** Reboot and check installation."
        self.assertEqual(fit_common.remote_shell(
            "touch /etc/default/on-dhcp-proxy /etc/default/on-http /etc/default/on-tftp /etc/default/on-syslog /etc/default/on-taskgraph"
        )['exitcode'], 0, "Install failure.")
        # reboot
        print "**** Rebooting appliance..."
        fit_common.remote_shell("shutdown -r now")
        print "**** Waiting for login..."
        fit_common.countdown(30)
        shell_data = 0
        for dummy in range(0, 30):
            shell_data = fit_common.remote_shell("pwd")
            if shell_data['exitcode'] == 0:
                break
            else:
                fit_common.time.sleep(5)
        self.assertEqual(shell_data['exitcode'], 0, "Shell test failed after appliance reboot")
        fit_common.time.sleep(10)
        self.assertEqual(fit_common.rackhdapi("/api/1.1/config")['status'], 200, "Unable to contact RackHD.")

if __name__ == '__main__':
    fit_common.unittest.main()