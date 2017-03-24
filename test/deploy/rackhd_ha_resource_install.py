"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.
This script prepares the RackHD HA cluster resources

This script perform the following functions:
    - configure mongo resource
    - configure mongo virtual ips
    - colocate mongo resource with virtual ip
    - create mongo replica set

usage:
    python run_tests.py -stack <stack ID> -test deploy/rackhd_ha_resource_install.py -numvms <num>
"""
from jinja2 import Environment, FileSystemLoader
import os
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


if __name__ == '__main__':
    unittest.main()
