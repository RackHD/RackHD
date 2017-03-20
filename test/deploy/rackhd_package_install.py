'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

This script installs RackHD from BIntray packages onto blank Ubuntu 14 or 16 OS via Ansible installer.
If test bed is behind proxy wall, make sure to enter proxy URL in config/install_default.json
This script performs the following functions:
    - loads prerequisite packages git, ansible, etc.
    - downloads RackHD source to management server
    - installs using rackhd_package.yml playbook
    - set up networking
    - load configuration files
    - startup and verify operations

usage:
    python run_tests.py -stack <stack ID> -test deploy/rackhd_package_install.py
'''

import fit_path  # NOQA: unused import

import os
import sys
import subprocess
import fit_common

# set proxy if required
PROXYVARS = ''
if fit_common.fitproxy()['host'] != '':
    # note that both proxy server settings below are set to the same http: URL
    PROXYVARS = "export http_proxy=http://" + fit_common.fitproxy()['host'] + ":" + fit_common.fitproxy()['port'] + ";" + \
                "export https_proxy=http://" + fit_common.fitproxy()['host'] + ":" + fit_common.fitproxy()['port'] + ";"

class rackhd_package_install(fit_common.unittest.TestCase):
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
        print "**** Cloning RackHD repo."
        # clone base repo
        fit_common.remote_shell('rm -rf ~/rackhd')
        self.assertEqual(fit_common.remote_shell(PROXYVARS + "git clone "
                                                + fit_common.fitinstall()['rackhd']['repo']
                                                + " ~/rackhd"
                                                )['exitcode'], 0, "RackHD git clone failure.")

    def test03_run_ansible_installer(self):
        print "**** Run RackHD Ansible installer."
        self.assertEqual(fit_common.remote_shell(PROXYVARS +
                                                 "cd ~/rackhd/packer/ansible/;"
                                                 "ansible-playbook -i 'local,' -c local rackhd_package.yml",
                                                 timeout=800,
                                                 )['exitcode'], 0, "RackHD Install failure.")

    def test04_install_network_config(self):
        print "**** Installing RackHD network config."
        # collect nic names
        getifs = fit_common.remote_shell("ifconfig -s -a |tail -n +2 |grep -v -e Iface -e lo -e docker")
        # clean out login stuff
        splitifs = getifs['stdout'].split('\n')
        ifslist = [] # array of valid eth ports
        for item in splitifs:
            if "assword" not in item and item.split(" ")[0]:
                ifslist.append(item.split(" ")[0])

        # install control network config
        control_cfg = open('control.cfg', 'w')
        control_cfg.write(
                            'auto ' + ifslist[1] + '\n'
                            'iface ' + ifslist[1] + ' inet static\n'
                            'address 172.31.128.1\n'
                            'netmask 255.255.252.0\n'
                        )
        control_cfg.close()
        # copy file to ORA
        fit_common.scp_file_to_ora('control.cfg')
        self.assertEqual(fit_common.remote_shell('cp control.cfg /etc/network/interfaces.d/')['exitcode'], 0, "Control network config failure.")
        os.remove('control.cfg')
        # startup NIC
        fit_common.remote_shell('ip addr add 172.31.128.1/22 dev ' + ifslist[1])
        fit_common.remote_shell('ip link set ' + ifslist[1] + ' up')
        self.assertEqual(fit_common.remote_shell('ping -c 1 -w 5 172.31.128.1')['exitcode'], 0, 'Control NIC failure.')

        # If PDU network adapter is present, configure
        try:
            ifslist[2]
        except IndexError:
            print "**** No PDU network will be configured"
        else:
            pdudirect_cfg = open('pdudirect.cfg', 'w')
            pdudirect_cfg.write(
                                'auto ' + ifslist[2] + '\n'
                                'iface ' + ifslist[2] + ' inet static\n'
                                'address 192.168.1.1\n'
                                'netmask 255.255.255.0\n'
                                )
            pdudirect_cfg.close()
            # copy file to ORA
            fit_common.scp_file_to_ora('pdudirect.cfg')
            self.assertEqual(fit_common.remote_shell('cp pdudirect.cfg /etc/network/interfaces.d/')['exitcode'], 0, "DHCP Config failure.")
            os.remove('pdudirect.cfg')
            # startup NIC
            fit_common.remote_shell('ip addr add 192.168.1.1/24 dev ' + ifslist[2])
            fit_common.remote_shell('ip link set ' + ifslist[2] + ' up')
            self.assertEqual(fit_common.remote_shell('ping -c 1 -w 5 192.168.1.1')['exitcode'], 0, 'PDU NIC failure.')

        #create DHCP config
        fit_common.remote_shell('echo INTERFACES=' + ifslist[1] + ' > /etc/default/isc-dhcp-server')
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
        hdconfig = fit_common.fitcfg()['rackhd-config']
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

    def test06_startup(self):
        print "Restart services."
        self.assertEqual(fit_common.remote_shell("service isc-dhcp-server restart")['exitcode'], 0, "isc-dhcp-server failure.")
        self.assertEqual(fit_common.remote_shell("service on-http restart")['exitcode'], 0, "on-http failure.")
        self.assertEqual(fit_common.remote_shell("service on-dhcp-proxy restart")['exitcode'], 0, "on-dhcp-proxy failure.")
        self.assertEqual(fit_common.remote_shell("service on-syslog restart")['exitcode'], 0, "on-syslog failure.")
        self.assertEqual(fit_common.remote_shell("service on-taskgraph restart")['exitcode'], 0, "on-taskgraph failure.")
        self.assertEqual(fit_common.remote_shell("service on-tftp restart")['exitcode'], 0, "on-tftp failure.")
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
    
