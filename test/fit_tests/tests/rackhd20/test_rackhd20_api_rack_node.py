'''
Copyright 2016, EMC, Inc.

Author(s):
Norton Luo

'''

import os
import sys
import json
import time
import string
import random
import urllib
from datetime import *
import time
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common
import test_api_utils




def get_node_list():
    mon_url = '/api/1.1/nodes'
    response = fit_common.rackhdapi(mon_url)
    nodefound = response['json']
    return nodefound

def get_compute_node_list():
    mon_url = '/api/1.1/nodes'
    response = fit_common.rackhdapi(mon_url)
    nodefound=[]
    if response['status'] in range(200,205):
        for nodes in response['json']:
            if nodes["type"]=="compute":
                nodefound.append(nodes["id"])
    print "compute list=",nodefound
    return nodefound

def get_switch_node_list():
    mon_url = '/api/1.1/nodes'
    response = fit_common.rackhdapi(mon_url)
    nodefound=[]
    if response['status'] in range(200,205):
        for nodes in response['json']:
            if nodes["type"]=="switch":
                nodefound.append(nodes["id"])
    print "switch list=",nodefound
    return nodefound

def add_relation(hostnode,slavenode):
    mon_url = '/api/2.0/nodes/{}/relations'.format(hostnode)
    response= fit_common.rackhdapi(mon_url,action='put',payload={"contains": [slavenode]})
    if response['status'] in range(200,205):
         return 1
    else:
         return 0

def check_relation(hostnode,slavenode):
    mon_url = '/api/2.0/nodes/{}/relations'.format(hostnode)
    response= fit_common.rackhdapi(mon_url)
    if response['status'] in range(200,205):
        for relation in response['json']:
            if relation["relationType"]== "contains":
                if slavenode in relation["targets"]:
                    return 1
    return 0

def delete_relations(hostnode):
    mon_url = '/api/2.0/nodes/{}/relations'.format(hostnode)
    response= fit_common.rackhdapi(mon_url)
    if len(response["text"])<3:
        return 1
    if response['status'] in range(200,205):
        for relation in response['json']:
            if relation["relationType"]== "contains":
                for slavenode in relation["targets"]:
                    response= fit_common.rackhdapi(mon_url,action='delete',payload={"contains": [slavenode]})
                    if response['status'] in range(200,205):
                        if check_relation(hostnode,slavenode)== 0:
                            continue
                        else:
                            return 0
                    else:
                        return 0
    return 1

def get_pdu_node_list():
    mon_url = '/api/1.1/nodes'
    response = fit_common.rackhdapi(mon_url)
    nodefound=[]
    if response['status'] in range(200,205):
        for nodes in response['json']:
            if nodes["type"]=="pdu":
                nodefound.append(nodes["id"])
    print "pdu list=",nodefound
    return nodefound

def get_rack_node_list():
    mon_url = '/api/1.1/nodes'
    response = fit_common.rackhdapi(mon_url)
    nodefound=[]
    if response['status'] in range(200,205):
        for nodes in response['json']:
            if nodes["type"]=="rack":
                nodefound.append(nodes["id"])
    print "pdu list=",nodefound
    return nodefound


# Select nose.plugins.attrib import attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class rackhd20_api_rack_node(fit_common.unittest.TestCase):
    #clear the test environment
    def tear_down(self):
        self.test_api_delete_relation()
        self.test_api_delete_rack()


    def test_api_create_and_check_racks(self):
        for operator in range(0,257):
            RandomCharacters = '.'.join(random.sample(string.printable,8))
            rackname = "myRack" + "_" + " " + RandomCharacters + datetime.now().__str__() + " " + RandomCharacters
            Newrack = {"name" :rackname,"type":"rack"}
            print "create new tag: " ,Newrack
            mon_url = '/api/1.1/nodes'
            mon_data = fit_common.rackhdapi(mon_url,action='post',payload=Newrack)
            self.assertIn(mon_data['status'],range(200,205),"Incorrect HTTP return code: {}".format(mon_data['status']))
            rackid = mon_data['json']['id']
            mon_url = '/api/1.1/nodes/{}'.format(rackid)
            mon_data = fit_common.rackhdapi(mon_url)
            self.assertIn(mon_data['status'],range(200,205),"Incorrect HTTP return code: {}".format(mon_data['status']))
            json_node_data = mon_data['json']
            self.assertTrue(json_node_data['name'] == Newrack['name'] and json_node_data['type']=="rack","rack node field error")
            print "query rack: " + rackname + "successfully!"
    print "test: rack creation and query succeed!"

    def test_api_delete_rack(self):
        rack_node_list= get_rack_node_list()
        for rack in rack_node_list:
            mon_url = '/api/1.1/nodes/{}'.format(rack)
            mon_data = fit_common.rackhdapi(mon_url,action='delete')
            self.assertIn(mon_data['status'],range(200,205),"Incorrect HTTP return code: {}".format(mon_data['status']))

    def test_api_add_relation(self):
        rack_node_list= get_rack_node_list()
        compute_node_list= get_compute_node_list()
        switch_node_list= get_switch_node_list()
        pdu_node_list= get_pdu_node_list()
        add_relation(rack_node_list[10],compute_node_list[1])
        for index in range(0,8):
            print "n=",(2*index+1)
            add_relation(rack_node_list[index],compute_node_list[(2*index+1)])
            add_relation(rack_node_list[index],compute_node_list[(2*index)])
            if switch_node_list!=[]:
                add_relation(rack_node_list[index],switch_node_list[index])
            if pdu_node_list!=[]:
                add_relation(rack_node_list[index],pdu_node_list[index])
            self.assertLessEqual(check_relation(rack_node_list[index],compute_node_list[(2*index+1)]),1,"Fail to check the relation")
            self.assertLessEqual(check_relation(rack_node_list[index],compute_node_list[(2*index)]),1,"Fail to check the relation")
            if switch_node_list!=[]:
                self.assertLessEqual(check_relation(rack_node_list[index],switch_node_list[index]),1,"Fail to check the relation")
            if pdu_node_list!=[]:
                self.assertLessEqual(check_relation(rack_node_list[index],pdu_node_list[index]),1,"Fail to check the relation")


    def test_api_delete_relation(self):
        rack_node_list= get_rack_node_list()
        for rack_node in rack_node_list:
            self.assertEqual(delete_relations(rack_node),1,"Fail to clear up relation on rack ")



if __name__ == '__main__':
    fit_common.unittest.main()
