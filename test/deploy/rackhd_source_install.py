'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

This script installs RackHD from GitHub source onto blank Ubuntu 14 or 16 OS via Ansible installer.
This script performs the following functions:
    - loads prerequisite packages git, ansible, etc.
    - downloads RackHD source to management server from fit_common.fit_install()
    - installs using rackhd_local.yml playbook
    - set up networking
    - load configuration files
    - startup and verify operations

NOTES:
       If the host is rebooted, the RackHD must be restarted by typing 'sudo nf start' at console.

usage:
    python run_tests.py -ova <ip or host> -test deploy/rackhd_source_install.py
    or
    python run_tests.py -stack <stack ID> -test deploy/rackhd_source_install.py
'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# set proxy if required
PROXYVARS = ''
if fit_common.fitproxy()['host'] != '':
    PROXYVARS = "export http_proxy=http://" + fit_common.fitproxy()['host'] + ":" + fit_common.fitproxy()['port'] + ";" + \
                "export https_proxy=http://" + fit_common.fitproxy()['host'] + ":" + fit_common.fitproxy()['port'] + ";"
    # maven proxy settings
    maven_proxy = open('settings.xml', 'w')
    maven_proxy.write(
      '<settings '
      'xmlns="http://maven.apache.org/SETTINGS/1.0.0" '
      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
      'xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0 '
      'http://maven.apache.org/xsd/settings-1.0.0.xsd">'
          '<proxies>'
              '<proxy>'
              '<id>mavenproxy</id>'
              '<active>true</active>'
              '<protocol>https</protocol>'
              '<host>' + fit_common.fitproxy()['host'] + '</host>'
              '<port>' + fit_common.fitproxy()['port'] + '</port>'
              '<nonProxyHosts>localhost</nonProxyHosts>'
            '</proxy>'
          '</proxies>'
      '</settings>')
    maven_proxy.close()
    fit_common.scp_file_to_ora('settings.xml')
    fit_common.remote_shell('mkdir -p ~/.m2;cp settings.xml ~/.m2;mkdir -p /root/.m2;cp settings.xml /root/.m2')
    os.remove('settings.xml')

class rackhd_source_install(fit_common.unittest.TestCase):
    def test01_install_rackhd_dependencies(self):
        print "**** Installing RackHD dependencies."
        # update sudoers to preserve proxy environment
        sudoersproxy = open("sudoersproxy", 'w')
        sudoersproxy.write('Defaults env_keep="HOME no_proxy http_proxy https_proxy"\n')
        sudoersproxy.close()
        fit_common.remote_shell('pwd')
        fit_common.scp_file_to_ora("sudoersproxy")
        self.assertEqual(fit_common.remote_shell('cp sudoersproxy /etc/sudoers.d/'
                                                  )['exitcode'], 0, "sudoersproxy config failure.")
        os.remove('sudoersproxy')
        # install git
        self.assertEqual(fit_common.remote_shell(PROXYVARS + "apt-get -y install git")['exitcode'], 0, "Git install failure.")
        self.assertEqual(fit_common.remote_shell("git config --global http.sslverify false")['exitcode'], 0, "Git config failure.")
        if fit_common.fitproxy()['host'] != '':
            self.assertEqual(fit_common.remote_shell("git config --global http.proxy http://" + fit_common.fitproxy()['host'] + ':' + fit_common.fitproxy()['port']
                                                  )['exitcode'], 0, "Git proxy config failure.")
        # install Ansible
        self.assertEqual(fit_common.remote_shell(PROXYVARS + "apt-get -y update")['exitcode'], 0, "Update failure.")
        self.assertEqual(fit_common.remote_shell(PROXYVARS + "cd ~;apt-get -y install ansible")['exitcode'], 0, "Ansible Install failure.")
        # create startup files
        self.assertEqual(fit_common.remote_shell(
            "touch /etc/default/on-dhcp-proxy /etc/default/on-http /etc/default/on-tftp /etc/default/on-syslog /etc/default/on-taskgraph"
            )['exitcode'], 0, "Startup files failure.")

    def test02_clone_rackhd_source(self):
        print "**** Cloning RackHD source."
        modules = [
            "on-core",
            "on-dhcp-proxy",
            "on-http",
            "on-statsd",
            "on-syslog",
            "on-taskgraph",
            "on-tasks",
            "on-tftp",
            "on-tools",
            "on-wss"
        ]
        # clone base repo
        fit_common.remote_shell('rm -rf ~/rackhd')
        self.assertEqual(fit_common.remote_shell(PROXYVARS + "git clone "
                                                + fit_common.fitinstall()['rackhd']['repo']
                                                + " ~/rackhd"
                                                )['exitcode'], 0, "RackHD git clone failure.")
        self.assertEqual(fit_common.remote_shell("cd ~/rackhd/" + ";git checkout "
                                                 + fit_common.fitinstall()['rackhd']['branch']
                                                 )['exitcode'], 0, "Branch not found on RackHD repo.")
        # clone modules
        for repo in modules:
            self.assertEqual(fit_common.remote_shell(PROXYVARS
                                                    + "rm -rf ~/rackhd/" + repo + ";"
                                                    + "git clone "
                                                    + fit_common.fitinstall()[repo]['repo']
                                                    + " ~/rackhd/" + repo
                                                     )['exitcode'], 0, "RackHD git clone module failure:" + repo)
            self.assertEqual(fit_common.remote_shell("cd ~/rackhd/" + repo + ";git checkout "
                                                     + fit_common.fitinstall()[repo]['branch']
                                                     )['exitcode'], 0, "Branch not found on module:" + repo)

    def test03_run_ansible_installer(self):
        print "**** Run RackHD Ansible installer."
        self.assertEqual(fit_common.remote_shell(PROXYVARS +
                                                 "cd ~/rackhd/packer/ansible/;"
                                                 "ansible-playbook -i 'local,' -c local rackhd_local.yml",
                                                 timeout=2000,
                                                 )['exitcode'], 0, "RackHD Install failure.")

    def test04_install_network_config(self):
        print "**** Installing RackHD network config."
        # collect nic names
        getifs = fit_common.remote_shell("ifconfig -s -a |tail -n +2 |grep -v -e Iface -e lo")
        # clean out login stuff
        splitifs = getifs['stdout'].split('\n')
        ifslit = [] # array of valid eth ports
        for item in splitifs:
            if "assword" not in item and item.split(" ")[0]:
                ifslit.append(item.split(" ")[0])

        # install control network config
        control_cfg = open('control.cfg', 'w')
        control_cfg.write(
                            'auto ' + ifslit[1] + '\n'
                            'iface ' + ifslit[1] + ' inet static\n'
                            'address 172.31.128.1\n'
                            'netmask 255.255.252.0\n'
                        )
        control_cfg.close()
        # copy file to ORA
        fit_common.scp_file_to_ora('control.cfg')
        self.assertEqual(fit_common.remote_shell('cp control.cfg /etc/network/interfaces.d/')['exitcode'], 0, "Control network config failure.")
        os.remove('control.cfg')
        # startup NIC
        fit_common.remote_shell('ip addr add 172.31.128.1/22 dev ' + ifslit[1])
        fit_common.remote_shell('ip link set ' + ifslit[1] + ' up')
        self.assertEqual(fit_common.remote_shell('ping -c 1 -w 5 172.31.128.1')['exitcode'], 0, 'Control NIC failure.')

        # If PDU network adapter is present, configure
        try:
            ifslit[2]
        except IndexError:
            print "**** No PDU network will be configured"
        else:
            pdudirect_cfg = open('pdudirect.cfg', 'w')
            pdudirect_cfg.write(
                                'auto ' + ifslit[2] + '\n'
                                'iface ' + ifslit[2] + ' inet static\n'
                                'address 192.168.1.1\n'
                                'netmask 255.255.255.0\n'
                                )
            pdudirect_cfg.close()
            # copy file to ORA
            fit_common.scp_file_to_ora('pdudirect.cfg')
            self.assertEqual(fit_common.remote_shell('cp pdudirect.cfg /etc/network/interfaces.d/')['exitcode'], 0, "DHCP Config failure.")
            os.remove('pdudirect.cfg')
            # startup NIC
            fit_common.remote_shell('ip addr add 192.168.1.1/24 dev ' + ifslit[2])
            fit_common.remote_shell('ip link set ' + ifslit[2] + ' up')
            self.assertEqual(fit_common.remote_shell('ping -c 1 -w 5 192.168.1.1')['exitcode'], 0, 'PDU NIC failure.')

        #create DHCP config
        fit_common.remote_shell('echo INTERFACES=' + ifslit[1] + ' > /etc/default/isc-dhcp-server')
        dhcp_conf = open('dhcpd.conf', 'w')
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
        # copy file to ORA
        fit_common.scp_file_to_ora('dhcpd.conf')
        self.assertEqual(fit_common.remote_shell('cp dhcpd.conf /etc/dhcp/')['exitcode'], 0, "DHCP Config failure.")
        os.remove('dhcpd.conf')

    def test05_install_rackhd_config_files(self):
        print "**** Installing RackHD config files."
        # create RackHD config
        hdconfig = {
                    "CIDRNet": "172.31.128.0/22",
                    "amqp": "amqp://localhost",
                    "apiServerAddress": "172.31.128.1",
                    "apiServerPort": 9080,
                    "arpCacheEnabled": True,
                    "broadcastaddr": "172.31.131.255",
                    "dhcpGateway": "172.31.128.1",
                    "dhcpProxyBindAddress": "172.31.128.1",
                    "dhcpProxyBindPort": 4011,
                    "dhcpSubnetMask": "255.255.252.0",
                    "gatewayaddr": "172.31.128.1",
                    "httpEndpoints": [
                        {
                            "address": "0.0.0.0",
                            "port": fit_common.fitports()['http'],
                            "httpsEnabled": False,
                            "proxiesEnabled": True,
                            "authEnabled": False,
                            "routers": "northbound-api-router"
                        },
                        {
                            "address": "0.0.0.0",
                            "port": fit_common.fitports()['https'],
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
                    "httpProxies": fit_common.fitrackhd()['httpProxies'],
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
                }
        config_json = open('config.json', 'w')
        config_json.write(fit_common.json.dumps(hdconfig, sort_keys=True, indent=4))
        config_json.close()
        # AMQP config files
        rabbitmq_config = open('rabbitmq.config', 'w')
        rabbitmq_config.write('[{rabbit,[{tcp_listeners, [5672]},{loopback_users, []}]},{rabbitmq_management,[{listener, [{port,  15672},{ip,"127.0.0.1"}]}]}].')
        rabbitmq_config.close()
        # copy files to ORA
        fit_common.scp_file_to_ora('config.json')
        fit_common.scp_file_to_ora('rabbitmq.config')
        self.assertEqual(fit_common.remote_shell('cp config.json /opt/monorail/')['exitcode'], 0, "RackHD Config file failure.")
        self.assertEqual(fit_common.remote_shell('cp rabbitmq.config /etc/rabbitmq/')['exitcode'], 0, "AMQP Config file failure.")
        os.remove('config.json')
        os.remove('rabbitmq.config')
        fit_common.remote_shell('mkdir -p ~/src/on-http/static/swagger-ui')

    def test06_startup(self):
        print "Start services."
        startup = open('startup.sh', 'w')
        startup.write('cd ~/;nf start&\n')
        startup.close()
        fit_common.scp_file_to_ora('startup.sh')
        self.assertEqual(fit_common.remote_shell("chmod 777 startup.sh;/etc/init.d/isc-dhcp-server restart")['exitcode'], 0, "dhcp startup failure.")
        self.assertEqual(fit_common.remote_shell("nohup ./startup.sh")['exitcode'], 0, "RackHD startup failure.")
        print "**** Check installation."
        for dummy in range(0, 10):
            try:
                fit_common.rackhdapi("/api/2.0/config")
            except:
                fit_common.time.sleep(10)
            else:
                break
        self.assertEqual(fit_common.rackhdapi("/api/2.0/config")['status'], 200, "Unable to contact RackHD.")

if __name__ == '__main__':
    fit_common.unittest.main()
