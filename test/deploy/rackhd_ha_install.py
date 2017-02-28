"""
Copyright (c) 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

This script prepares the VMs for an HA clustered configuration
This is for setting up a cluster to do HA development and testing.


This script performs the following functions:
    - Configures the control network for each node in the cluster
    - installs the DHCP configuration
    - sets the /etc/hosts config
    - sets the hostname

usage:
    python run_tests.py -stack <stack ID> -test deploy/rackhd_ha_install.py -numvms <num>
"""
from jinja2 import Environment, FileSystemLoader
import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import unittest
import time
from nosedep import depends
import fit_common

ifslist = []   # array of valid eth ports
numvms = int(fit_common.fitargs()['numvms'])


class rackhd_ha_install(unittest.TestCase):

    def test01_install_network_config(self):
        for vmnum in range(1, numvms + 1):

            # collect nic names
            getifs = fit_common.remote_shell("ifconfig -s -a |tail -n +2 |grep -v -e Iface -e lo -e docker", vmnum=vmnum)
            # clean out login stuff
            splitifs = getifs['stdout'].split('\n')
            for item in splitifs:
                if "assword" not in item and item.split(" ")[0]:
                    ifslist.append(item.split(" ")[0])

            self.assertNotEqual(len(ifslist), 0, "Found no interfaces for node {}".format(vmnum))
            control_ip = '172.31.128.{}'.format(vmnum)

            # install control network config
            control_cfg = open('control.cfg', 'w')
            control_cfg.write('auto ' + ifslist[1] + '\n'
                              'iface ' + ifslist[1] + ' inet static\n'
                              'address ' + control_ip + '\n'
                              'netmask 255.255.252.0\n')
            control_cfg.close()
            # copy file to ORA
            fit_common.scp_file_to_host('control.cfg', vmnum)
            os.remove('control.cfg')
            self.assertEqual(fit_common.remote_shell('cp control.cfg /etc/network/interfaces.d/', vmnum=vmnum)['exitcode'],
                             0, "Control network config failure.")
            # startup NIC
            fit_common.remote_shell('ip addr add ' + control_ip + '/22 dev ' + ifslist[1], vmnum=vmnum)
            fit_common.remote_shell('ip link set ' + ifslist[1] + ' up', vmnum=vmnum)
            self.assertEqual(fit_common.remote_shell('ping -c 1 -w 5 ' + control_ip, vmnum=vmnum)['exitcode'],
                             0, 'Control NIC failure.')

    def reboot_node(self, vmnum):
        address = ""
        if (vmnum == 1):
            address = fit_common.fitargs()['rackhd_host']
        else:
            address = fit_common.fitargs()['rackhd_host'].replace("ora", "ora-" + str(vmnum - 1))

        fit_common.remote_shell('shutdown -r now', vmnum=vmnum)
        time.sleep(3)

        for i in range(0, 15):
            if subprocess.call("ping -c 1 -w 5 " + address, shell=True) == 0:
                return True
            time.sleep(1)

        return False

    def test06_restart_nodes(self):
        for vmnum in range(1, numvms + 1):
            self.assertTrue(self.reboot_node(vmnum), "Failed to reboot node {}".format(vmnum))

    @depends(after=test01_install_network_config, before=test06_restart_nodes)
    def test02_install_dhcp_config(self):
        # create DHCP config
        for vmnum in range(1, numvms + 1):
            fit_common.remote_shell('echo INTERFACES=' + ifslist[1] + ' > /etc/default/isc-dhcp-server', vmnum=vmnum)
            dhcp_conf = open('dhcpd.conf', 'w')
            dhcp_conf.write('ddns-update-style none;\n'
                            'option domain-name "example.org";\n'
                            'option domain-name-servers ns1.example.org, ns2.example.org;\n'
                            'default-lease-time 600;\n'
                            'max-lease-time 7200;\n'
                            'log-facility local7;\n'
                            'deny duplicates;\n'
                            'ignore-client-uids true;\n'
                            'subnet 172.31.128.0 netmask 255.255.252.0 {\n'
                            '  range 172.31.128.100 172.31.131.254;\n'
                            '  option vendor-class-identifier "PXEClient";\n'
                            '}\n')
            dhcp_conf.close()
            # copy file to ORA
            fit_common.scp_file_to_host('dhcpd.conf', vmnum)
            os.remove('dhcpd.conf')
            self.assertEqual(fit_common.remote_shell('cp dhcpd.conf /etc/dhcp/', vmnum=vmnum)['exitcode'],
                             0, "DHCP Config failure.")

    def create_hosts(self):
        hosts_conf = open('hosts-conf', 'w')
        for vmnum in range(1, numvms + 1):
            line = '172.31.128.{}\tnode{}\n'.format(vmnum, vmnum)
            hosts_conf.write(line)
        hosts_conf.close()

    def create_node_list(self):
        result = ""
        sb_net = self.get_southbound_network()
        if sb_net:
            for vmnum in range(1, numvms + 1):
                result += "   node {{\n      ring0_addr: {1}.{0}\n      nodeid: {0}\n   }}\n".format(vmnum, sb_net)
        return result

    def find_southbound(self, httpEndpoints):
        for i in httpEndpoints:
            if i["routers"] == "southbound-api-router":
                return i
        return None

    def get_template_file(self, file_name):
        template_folder = './config_templates'
        env = Environment(loader=FileSystemLoader(template_folder))
        return env.get_template(file_name)

    def get_southbound_network(self):
        endpoints = fit_common.fitrackhd()['httpEndpoints']
        southbound = self.find_southbound(endpoints)
        if southbound and 'address' in southbound:
            address = southbound["address"]
            addrsplit = address.split('.')
            return("{}.{}.{}".format(addrsplit[0], addrsplit[1], addrsplit[2]))
        return None

    def create_corosync_config(self):
        template = self.get_template_file("corosync_config")
        rendered = template.render(node_list=self.create_node_list())
        return rendered

    @depends(before=test06_restart_nodes)
    def test03_install_hosts_config(self):
        sb_net = self.get_southbound_network()
        self.assertIsNotNone(sb_net, "Could not find southbound address")

        for vmnum in range(1, numvms + 1):
            self.create_hosts()
            # copy file to ORA
            fit_common.scp_file_to_host('hosts-conf', vmnum)
            # Clean out the previous entries to be idempotent
            command = "grep -v {} /etc/hosts > hosts".format(sb_net)
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'],
                             0, "Hosts Config failure; Cleaning out previous entries")
            # Replace the local hostname
            command = "sed -i 's/ora/node{}/' hosts".format(vmnum)
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'],
                             0, "Hosts Config failure; Replacing local hostname")
            # Add the new entries
            self.assertEqual(fit_common.remote_shell('cat hosts-conf >> hosts', vmnum=vmnum)['exitcode'],
                             0, "Hosts Config failure; Adding new entries")
            # Move the new file into place
            self.assertEqual(fit_common.remote_shell('mv hosts /etc/hosts', vmnum=vmnum)['exitcode'],
                             0, "Hosts Config failure; Moving new file into place")
        os.remove('hosts-conf')

    @depends(before=test06_restart_nodes)
    def test04_install_hostname_config(self):
        for vmnum in range(1, numvms + 1):
            command = "echo node{} > /etc/hostname".format(vmnum)
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'], 0, "Hostname Config failure.")

    @depends(before=test06_restart_nodes)
    def test05_install_corosync_config(self):
        corosync_conf = open('corosync.conf', 'w')
        corosync_conf.write(self.create_corosync_config())
        corosync_conf.close()
        for vmnum in range(1, numvms + 1):
            # copy file to ORA
            fit_common.scp_file_to_host('corosync.conf', vmnum)
            self.assertEqual(fit_common.remote_shell('cp corosync.conf /etc/corosync/', vmnum=vmnum)['exitcode'],
                             0, "Corosync Config failure.")
        os.remove('corosync.conf')

    def is_service_up(self, service, vmnum):
        command = 'service {} status | grep -q "running"'.format(service)
        rc = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
        return rc == 0

    def has_pending_nodes(self, vmnum):
        command = 'crm status | grep pending'
        status = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
        return status == 0

    def has_offline_nodes(self, vmnum):
        command = 'crm status | grep OFFLINE'
        status = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
        return status == 0

    def has_unclean_nodes(self, vmnum):
        command = 'crm status | grep UNCLEAN'
        status = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
        return status == 0

    @depends(after=test06_restart_nodes)
    def test07_clear_ora_node(self):
        # Pacemaker set up a default node previously that we can now clear out
        command = "crm node delete ora"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'],
                         0, "Failed to remove ora from pacemaker")

    @depends(after=test07_clear_ora_node)
    def test08_check_pacemaker_status(self):
        for vmnum in range(1, numvms + 1):
            # Check that corosync service is active and running
            self.assertTrue(self.is_service_up("corosync", vmnum), "Corosync not running on node {}".format(vmnum))
            # Check that pacemaker service is active and running
            self.assertTrue(self.is_service_up("pacemaker", vmnum), "Pacemaker not running on node {}".format(vmnum))
            # Check that there are no nodes in pending status
            self.assertFalse(self.has_pending_nodes(vmnum), "Pending nodes found on node {}".format(vmnum))
            # Check that there are no nodes in offline status
            self.assertFalse(self.has_offline_nodes(vmnum), "Offline nodes found on node {}".format(vmnum))
            # Check that there are no nodes with unclean status
            self.assertFalse(self.has_unclean_nodes(vmnum), "Unclean nodes found on node {}".format(vmnum))


if __name__ == '__main__':
    unittest.main()
