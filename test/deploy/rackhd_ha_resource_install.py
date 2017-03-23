"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
This script prepares the RackHD HA cluster resources

This script perform the following functions:
    - configure mongo and rabbitmq resource
    - configure mongo and rabbitmq virtual ips
    - colocate mongo and rabbitmq resource with virtual ip
    - create mongo replica set
    - create rabbitmq mirrored queue policies

usage:
    python run_tests.py -stack <stack ID> -test deploy/rackhd_ha_resource_install.py -numvms <num>
"""
from jinja2 import Environment, FileSystemLoader
import os
import time
import unittest
import fit_path  # NOQA: unused import
import fit_common

nodelist = []   # list of active nodes in cluster
numvms = int(fit_common.fitargs()['numvms'])
err = []
numrs = numvms - 1   # number of mongo resource
vip_dict = {'mongo': [], 'rabbit': [], 'rackhd': []}


class rackhd_ha_resource_install(unittest.TestCase):
    longMessage = True

    def setUp(self):
        # collect active nodes in cluster
        for vmnum in range(1, numvms + 1):
            command = "crm_mon -X | grep 'node{}.*online=.true' -q".format(vmnum)
            status = fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
            if status != 0:
                err.append('node{} is offline'.format(vmnum))
            else:
                nodelist.append(vmnum)

    def configure_virtual_ip_resource(self, vmnum, ip, rsc_ip):
        # check interface for virtual ip
        if "172.31.128" not in ip:
            nic = "ens160"
        else:
            nic = "ens192"
        command = ("crm configure primitive {} ocf:heartbeat:IPaddr2 " +
                   "params ip='{}' nic='{}' " +
                   "op monitor interval='10s' meta is-managed='true'").format(rsc_ip, ip, nic)
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

    def create_mongo_config(self, ip_list):
        template_folder = './config_templates'
        env = Environment(loader=FileSystemLoader(template_folder))
        template = env.get_template("mongo_init.bash")
        config = {'_id': 'mongo_rs', 'members': []}
        for idx, val in enumerate(ip_list):
            config['members'].append({'_id': idx, 'host': '{}:27017'.format(val)})
        rendered = template.render(mongo_list=config, mongo_addr=ip_list[0])
        return rendered

    def test01_install_mongo_resource(self):
        # create resource on first active node
        vmnum = nodelist[0]
        sb_net = self.get_southbound_network()
        self.assertIsNotNone(sb_net, "Could not find southbound address")
        for mongo in range(1, numrs + 1):
            # start mongo container as pacemaker resource
            rsc = 'docker_mongo_{}'.format(mongo)
            command = ("crm configure primitive {} ocf:heartbeat:docker " +
                       "params allow_pull=true image='registry.hwimo.lab.emc.com/mongo' " +
                       "run_opts=\\\'--privileged=true --net='host' -d -p 27017:27017\\\' " +
                       "run_cmd=\\\'--replSet mongo_rs --logpath /var/log/mongodb/mongod.log\\\' " +
                       "meta is-managed='true'").format(rsc)
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'], 0, "{} resource failure.".format(rsc))
            # create mongo virtual ip resource
            ip = '{}.12{}'.format(sb_net, mongo)
            vip_dict['mongo'].append(ip)
            rsc_ip = 'mongo_addr_{}'.format(mongo)
            self.assertTrue(self.configure_virtual_ip_resource(vmnum, ip, rsc_ip), "{} resource failure.".format(rsc_ip))
            # colocate mongo and virtual IPs
            mongo_cls = 'mongo{}'.format(mongo)
            command = "crm configure colocation {} inf: {} {}".format(mongo_cls, rsc, rsc_ip)
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'], 0, "colocation failure")
        # create mongo replica config
        mongo_rep = open('mongo_replica_init.bash', 'w')
        mongo_rep.write(self.create_mongo_config(vip_dict['mongo']))
        mongo_rep.close()
        # copy file to ora
        fit_common.scp_file_to_host('mongo_replica_init.bash', vmnum)
        os.remove('mongo_replica_init.bash')
        fit_common.remote_shell("chmod 777 mongo_replica_init.bash", vmnum=vmnum)['exitcode']
        # run script to initiate replica set
        self.assertEqual(fit_common.remote_shell("./mongo_replica_init.bash", vmnum=vmnum)['exitcode'],
                         0, "Mongo replica initiation failure")

    def install_amqp_config_file(self):
        # AMQP config file
        result = ""
        for rsnum in range(1, numrs + 1):
            result += " 'rabbit@rabbit{}',".format(rsnum)
        rabbit_list = result.rstrip(",")
        rabbitmq_config = open('rabbitmq.config', 'w')
        rabbitmq_config.write("[ { rabbit, [{ loopback_users, [ ] },{cluster_nodes, {[%s], disc}} ] } ]." % rabbit_list)
        rabbitmq_config.close()
        for vmnum in range(1, numvms +1):
            # copy file to ORA
            fit_common.scp_file_to_host('rabbitmq.config', vmnum)
            self.assertEqual(fit_common.remote_shell('mkdir -p /docker;cp rabbitmq.config /docker/', vmnum=vmnum)['exitcode'],
                             0, "rabbitMQ Config failure.")
        os.remove('rabbitmq.config')

    def install_rabbitmq_hostname_config(self, ip_list):
        # create rabbitmq hosts
        hosts_conf = open('hosts-conf', 'w')
        for rsnum in range(1, numrs + 1):
            line = '{}\trabbit{}\n'.format(ip_list[rsnum - 1], rsnum)
            hosts_conf.write(line)
        hosts_conf.close()
        # copy file to ORA
        for vmnum in range(1, numvms + 1):
            fit_common.scp_file_to_host('hosts-conf', vmnum)
            # Clean out the previous entries to be idempotent
            command = "grep -v rabbit /etc/hosts > hosts"
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'],
                             0, "Hosts Config failure; Cleaning out previous entries")
            # Add the new entries
            self.assertEqual(fit_common.remote_shell('cat hosts-conf >> hosts', vmnum=vmnum)['exitcode'],
                             0, "Hosts Config failure; Adding new entries")
            # Move the new file into place
            self.assertEqual(fit_common.remote_shell('mv hosts /etc/hosts', vmnum=vmnum)['exitcode'],
                             0, "Hosts Config failure; Moving new file into place")
        os.remove('hosts-conf')

    def set_rabbitmq_cluster_policy(self, vmnum, rabbit_rsc_list):
        # collect hostname for first rabbitmq resource
        command = "crm_resource -W -r {} | sed \\\'s/.*node//g\\\'".format(rabbit_rsc_list[0])
        rc = fit_common.remote_shell(command, vmnum=vmnum)
        # clean out login stuff
        splitnode = rc['stdout'].split('\n')
        for item in splitnode:
            if "assword" not in item and item.split(" ")[0]:
                node = int(item)
        # create file for policies
        template_folder = './config_templates'
        env = Environment(loader=FileSystemLoader(template_folder))
        template = env.get_template("rabbitmq_policy.bash")
        rendered = template.render()
        rabbitmq_policy = open('rabbitmq.bash', 'w')
        rabbitmq_policy.write(rendered)
        rabbitmq_policy.close()
        # copy file to ORA
        fit_common.scp_file_to_host('rabbitmq.bash', vmnum=node)
        fit_common.remote_shell("chmod 777 rabbitmq.bash", vmnum=node)
        self.assertEqual(fit_common.remote_shell("./rabbitmq.bash", vmnum=node)['exitcode'],
                         0, "Rabbitmq mirrored queue policy failure.")

    def test02_install_rabbitmq_resource(self):
        # install rabbitmq config on cluster nodes
        self.install_amqp_config_file()
        # create resource on first active node
        vmnum = nodelist[0]
        sb_net = self.get_southbound_network()
        self.assertIsNotNone(sb_net, "Could not find southbound address")
        rabbitmq_rsc_list = []
        # set rabbitmq resource
        for rabbit in range(1, numrs + 1):
            rsc = 'docker_rabbit_{}'.format(rabbit)
            rabbitmq_rsc_list.append(rsc)
            command = ("crm configure primitive {} ocf:heartbeat:docker " +
                       "params allow_pull=true image='registry.hwimo.lab.emc.com/rabbitmq:management' " +
                       "run_opts=\\\'--privileged=true --net='host' -d -v /docker/rabbitmq.config:/etc/rabbitmq/rabbitmq.config " +
                       "-p 8080:15672 -p 4369:4369 -p 25672:25672 -p 5672:5672 -p 35197:35197 " +
                       "-e RABBITMQ_NODENAME=rabbit@rabbit{} -e RABBITMQ_ERLANG_COOKIE=secret_cookie_example\\\'").format(rsc, rabbit)
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'], 0, "{} resource failure".format(rsc))
            # configure virtual ip for rabbitmq resource
            ip = '{}.13{}'.format(sb_net, rabbit)
            vip_dict['rabbit'].append(ip)
            rsc_ip = 'rabbit_addr_{}'.format(rabbit)
            self.assertTrue(self.configure_virtual_ip_resource(vmnum, ip, rsc_ip), "{} resource failure.".format(rsc_ip))
            # colocate rabbitmq resource and virtual ip
            rabbit_cls = 'rabbit{}'.format(rabbit)
            command = "crm configure colocation {} inf: {} {}".format(rabbit_cls, rsc, rsc_ip)
            self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'],
                             0, "{} and {} colocation failure".format(rsc, rsc_ip))
        # put rabbitmq hostname on each node
        self.install_rabbitmq_hostname_config(vip_dict['rabbit'])
        # anti colocation between rabbit resources
        for index in range(len(rabbitmq_rsc_list)):
            for r_index in range(index + 1, len(rabbitmq_rsc_list)):
                command = "crm configure colocation rabbit_anti_{0}{1} -inf: {2} {3}" \
                          .format(index + 1, r_index + 1, rabbitmq_rsc_list[index], rabbitmq_rsc_list[r_index])
                self.assertEqual(fit_common.remote_shell(command, vmnum=vmnum)['exitcode'],
                                 0, "{} and {} anti colocation failure".format(rabbitmq_rsc_list[index], rabbitmq_rsc_list[r_index]))
        # restart rabbitmq resource
        for rsc in rabbitmq_rsc_list:
            command = "crm resource restart {}".format(rsc)
            fit_common.remote_shell(command, vmnum=vmnum)['exitcode']
            time.sleep(5)
        # set rabbitmq cluster policy for RackHD
        self.set_rabbitmq_cluster_policy(vmnum, rabbitmq_rsc_list)


if __name__ == '__main__':
    unittest.main()
