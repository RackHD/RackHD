"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved

This test checks the installation of the HA environment
"""

import fit_path  # NOQA: unused import
import unittest
import fit_common
# LOCAL
from nose.plugins.attrib import attr
from nosedep import depends

FAIL_ON_NODE_COLLECTION = True
MONGO_IP_PREFIX = '12'
RABBIT_IP_PREFIX = '13'

active_node_list = list()


@attr(regression=False, smoke=False, ha_resource_tests=True)
class HaResourceTest(unittest.TestCase):

    def setUp(self):
        self.number_of_vms = int(fit_common.fitargs()['numvms'])
        self.number_of_services = self.number_of_vms - 1  # number of mongo and rabbitmq resource

    def is_service_up(self, service, vmnum):
        command = 'service {} status | grep -q "running"'.format(service)
        rc = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
        return rc == 0

    def has_online_nodes(self, vmnum, node_name):
        command = 'crm status | grep Online | grep {}'.format(node_name)
        status = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
        return status == 0

    def has_resource(self, vmnum, resource):
        command = "crm resource show | grep '{}'".format(resource)
        rc = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
        return rc == 0

    def get_southbound_network(self):
        endpoints = fit_common.fitrackhd()['httpEndpoints']
        southbound = self.find_southbound(endpoints)
        if southbound and 'address' in southbound:
            address = southbound["address"]
            addrsplit = address.split('.')
            return("{}.{}.{}".format(addrsplit[0], addrsplit[1], addrsplit[2]))
        return None

    def find_southbound(self, httpEndpoints):
        for i in httpEndpoints:
            if i["routers"] == "southbound-api-router":
                return i
        return None

    def test010_check_pacemaker_status(self):
        for vmnum in range(1, self.number_of_vms + 1):
            # Check that corosync service is active and running
            self.assertTrue(self.is_service_up("corosync", vmnum), "Corosync not running on node {}".format(vmnum))
            # Check that pacemaker service is active and running
            self.assertTrue(self.is_service_up("pacemaker", vmnum), "Pacemaker not running on node {}".format(vmnum))

    def test011_check_default_configuration(self):
        err = ''
        for vmnum in range(1, self.number_of_vms + 1):
            # Check for default configuration
            if self.has_online_nodes(vmnum, 'ora'):
                err += (str(vmnum) + ', ')
        self.assertEqual(len(err), 0, "The following VMs have the default configuration: {}"
                         .format(err.rstrip(", ")))

    def test012_check_node_status(self):
        err = ''
        for vmnum in range(1, self.number_of_vms + 1):
            for node_number in range(1, self.number_of_vms + 1):
                # Determine if this node is online
                if not self.has_online_nodes(vmnum, 'node{}'.format(node_number)):
                    err += 'node{} on vm{}, '.format(node_number, vmnum)
        self.assertEqual(len(err), 0, "The following nodes are not online: {}"
                         .format(err.rstrip(", ")))

    def test020_check_and_collect_online_nodes(self):
        # determine node status and collect active nodes in cluster
        err = ''
        for vmnum in range(1, self.number_of_vms + 1):
            command = "crm_mon -X | grep 'node{}.*online=.true' -q".format(vmnum)
            status = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
            if status == 0:
                active_node_list.append(vmnum)
            else:
                err += 'node{}, '.format(vmnum)
        if FAIL_ON_NODE_COLLECTION:
            self.assertEqual(len(err), 0, 'The following nodes are offline: {}'
                             .format(err.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test030_check_mongo_resource(self):
        err = ''
        for mongo_number in range(1, self.number_of_services + 1):
            mongo_name = 'docker_mongo_{}'.format(mongo_number)
            if not self.has_resource(active_node_list[0], mongo_name):
                err += (mongo_name + ', ')
        self.assertEqual(len(err), 0, "The following Mongo resources are not present: {}"
                         .format(err.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test031_check_mongo_address_and_ip(self):
        err_addr = err_ip = ''

        # configure virtual ip for rabbitmq resource
        sb_net = self.get_southbound_network()
        self.assertIsNotNone(sb_net, 'Southbound network not found')

        for mongo_number in range(1, self.number_of_services + 1):
            # check for name
            command = "crm config show | grep 'primitive.*mongo_addr_{0}' -q" \
                      .format(mongo_number)
            status = fit_common.remote_shell(command, vmnum=active_node_list[0])['exitcode']
            if status != 0:
                err_addr += 'mongo_addr_{0}, '.format(mongo_number)
            else:
                # now check the IP address
                command = ("crm config show | grep -A3 'primitive.*mongo_addr_{0}'" +
                           " | grep 'ip={1}.{2}{0}' -q").format(mongo_number, sb_net, MONGO_IP_PREFIX)
                status = fit_common.remote_shell(command, vmnum=active_node_list[0])['exitcode']
                if status != 0:
                    err_ip += '{1}.{2}{0} for rabbit_addr_{0}, '.format(mongo_number, sb_net, MONGO_IP_PREFIX)

        self.assertEqual(len(err_addr), 0, 'The following Mongo addresses are missing: {}'
                         .format(err_addr.rstrip(", ")))
        self.assertEqual(len(err_ip), 0, 'The following Mongo IP addresses are missing or incorrect: {}'
                         .format(err_ip.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test032_check_mongo_colocation(self):
        err = ''
        for mongo_number in range(1, self.number_of_services + 1):
            command = "crm config show | grep 'mongo{0}.*inf:.*mongo_{0}.*addr_{0}' -q" \
                      .format(mongo_number)
            status = fit_common.remote_shell(command, vmnum=active_node_list[0])['exitcode']
            if status != 0:
                err += 'docker_mongo_{0} on mongo_addr_{0}, '.format(mongo_number)
        self.assertEqual(len(err), 0, 'The following Mongo coLocations are missing: {}'
                         .format(err.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test040_check_rabbit_resource(self):
        err = ''
        for rabbit_number in range(1, self.number_of_services + 1):
            rabbit_name = 'docker_rabbit_{}'.format(rabbit_number)
            if not self.has_resource(active_node_list[0], rabbit_name):
                err += (rabbit_name + ', ')
        self.assertEqual(len(err), 0, "The following Rabbit resources are not present: {}"
                         .format(err.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test041_check_rabbit_address_and_ip(self):
        err_addr = err_ip = ''

        # configure virtual ip for rabbitmq resource
        sb_net = self.get_southbound_network()
        self.assertIsNotNone(sb_net, 'Southbound network not found')

        for rabbit_number in range(1, self.number_of_services + 1):
            # check for name
            command = "crm config show | grep 'primitive.*rabbit_addr_{0}' -q" \
                      .format(rabbit_number)
            status = fit_common.remote_shell(command, vmnum=active_node_list[0])['exitcode']
            if status != 0:
                err_addr += ', '.format(rabbit_number)
            else:
                # now check the IP address
                command = ("crm config show | grep -A3 'primitive.*rabbit_addr_{0}'" +
                           " | grep 'ip={1}.{2}{0}' -q").format(rabbit_number, sb_net, RABBIT_IP_PREFIX)
                status = fit_common.remote_shell(command, vmnum=active_node_list[0])['exitcode']
                if status != 0:
                    err_ip += '{1}.{2}{0} for rabbit_addr_{0}, '.format(rabbit_number, sb_net, RABBIT_IP_PREFIX)

        self.assertEqual(len(err_addr), 0, 'The following rabbit addresses are missing: {}'
                         .format(err_addr.rstrip(", ")))
        self.assertEqual(len(err_ip), 0, 'The following rabbit IP addresses are missing or incorrect: {}'
                         .format(err_ip.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test042_check_rabbit_colocation(self):
        err = ''
        for rabbit_number in range(1, self.number_of_services + 1):
            command = "crm config show | grep 'rabbit{0}.*inf.*rabbit_{0}.*addr_{0}' -q" \
                      .format(rabbit_number)

            status = fit_common.remote_shell(command, vmnum=active_node_list[0])['exitcode']
            if status != 0:
                err += 'docker_rabbit_{0} on rabbit_addr_{0}, '.format(rabbit_number)
        self.assertEqual(len(err), 0, 'The following Rabbit coLocations are missing: {}'
                         .format(err.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test043_check_rabbit_anti_colocation(self):
        err = ''
        # for rabbit_number in range(1, self.number_of_services + 1):
        for index1 in range(1, self.number_of_services + 1):
            for index2 in range(index1 + 1, self.number_of_services + 1):
                command = "crm config show | grep 'anti_{0}{1}.*-inf:.*rabbit_{0}.*rabbit_{1}' -q" \
                          .format(index1, index2)
                status = fit_common.remote_shell(command, vmnum=active_node_list[0])['exitcode']
                if status != 0:
                    err += 'docker_rabbit_{0} on docker_rabbit_{1}, '.format(index1, index2)
        self.assertEqual(len(err), 0, 'The following Rabbit anti-coLocations are missing: {}'
                         .format(err.rstrip(", ")))

    @depends(after='test020_check_and_collect_online_nodes')
    def test050_check_rackhd_services(self):
        rackhd_list = ["docker_files",
                       "docker_isc-dhcp-server",
                       "docker_on-dhcp-proxy",
                       "docker_on-http",
                       "docker_on-syslog",
                       "docker_on-taskgraph",
                       "docker_on-tftp"]
        err = ''
        for rackhd_service in rackhd_list:
            if not self.has_resource(active_node_list[0], rackhd_service):
                err += (rackhd_service + ', ')
        self.assertEqual(len(err), 0, 'The following RackHd components are missing: {}'
                         .format(err.rstrip(", ")))
