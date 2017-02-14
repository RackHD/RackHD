'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo

'''
import json
from time import sleep
import os
import sys
import json
import time
import string
from datetime import *
import time
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common
import test_api_utils
import fit_amqp

amqp_message_received= False
routingkey=""
amqpbody=""


def get_node_list_by_type(type):
    mon_url = '/api/2.0/nodes'
    response = fit_common.rackhdapi(mon_url)
    nodefound=[]
    if response['status'] in range(200,205):
        for nodes in response['json']:
            if nodes["type"]==type:
                nodefound.append(nodes["id"])
    if fit_common.VERBOSITY >= 2:
        print type," list=",nodefound
    return nodefound

def amqpcallback(ch, method, properties, body):
    if fit_common.VERBOSITY >= 2:
        print(" Routing Key %r:" % (method.routing_key))
        print body #json.dumps(body, sort_keys=True, indent=4)
    global amqp_message_received
    global routingkey,amqpbody
    amqp_message_received=True
    amqpbody=body
    routingkey=method.routing_key


# Select nose.plugins.attrib import attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class amqp_rack_node(fit_common.unittest.TestCase):
    #clear the test environment
    def tear_down(self):
        self.test_api_delete_rack()

    def compare_message(self,expectedkey, expectedpayload):
        global routingkey, amqpbody
        self.assertEquals(routingkey, expectedkey, "No AMQP message received")
        try:
            amqp_body_json=fit_common.json.loads(amqpbody)
        except:
            print "FAILURE - The message body is not json format! "
            return False
        try:
            self.assertEquals(amqp_body_json['version'], expectedpayload['version'], "version field not correct!")
            self.assertEquals(amqp_body_json['typeId'], expectedpayload['typeId'], "typeId field not correct!")
            self.assertEquals(amqp_body_json['action'], expectedpayload['action'], "action field not correct!")
            self.assertEquals(amqp_body_json['severity'], expectedpayload['severity'], "serverity field not correct!")
            self.assertNotEquals(amqp_body_json['createdAt'], {}, "createdAt field not correct!")
            self.assertNotEquals(amqp_body_json['data'], {}, "createdAt field not correct!")
        except ValueError:
            print "FAILURE - expected key is missing in the AMQP message!"
            return False
        return True


    def test_api_create_and_check_racks(self):
        for operator in range(0,10):
            rackname = "myRack" + "_" + datetime.now().__str__()
            newrack = {"name" :rackname,"type":"rack"}
            if fit_common.VERBOSITY >= 2:
                print "create new tag: ", newrack
            mon_url = '/api/2.0/nodes'
            #start amqp thread
            global amqp_message_received, rackid, rackid
            amqp_message_received = False
            if fit_common.VERBOSITY >= 2:
                print 'launch AMQP thread'
            td = fit_amqp.AMQP_worker(exchange_name="on.events", routing_key="node.added.#",
                                      externalcallback=amqpcallback, timeout=10)
            td.setDaemon(True)
            td.start()
            mon_data_post = fit_common.rackhdapi(mon_url,action='post',payload=newrack)
            self.assertIn(mon_data_post['status'], range(200,205), "Incorrect HTTP return code: {}".format(mon_data_post['status']))
            rackid = mon_data_post['json']['id']
            mon_url = '/api/2.0/nodes/{}'.format(rackid)
            mon_data = fit_common.rackhdapi(mon_url)
            self.assertIn(mon_data['status'], range(200,205), "Incorrect HTTP return code: {}".format(mon_data['status']))
            json_node_data = mon_data['json']
            self.assertTrue(json_node_data['name'] == newrack['name'] and json_node_data['type']=="rack","rack node field error")
            timecount=0
            while amqp_message_received==False and timecount<10:
                sleep(1)
                timecount=timecount+1
            self.assertNotEquals(timecount, 10, "No AMQP message received")
            expectedkey="node.added.information."+rackid+'.'+rackid
            expectedpayload={"type": "node", "action": "added", "typeId": rackid,
                             "nodeId": rackid, "severity": "information", "version": "1.0",
                             "createdAt": mon_data_post['json']['createdAt']}
            self.assertEquals(self.compare_message(expectedkey, expectedpayload), True, "AMQP Message Check Error!")
            if fit_common.VERBOSITY >= 2:
                print "query rack: " + rackname + "successfully!"
        if fit_common.VERBOSITY >= 2:
            print "test: rack creation and query succeed!"

    def test_api_delete_rack(self):
        rack_node_list = get_node_list_by_type("rack")
        for rack in rack_node_list:
            global amqp_message_received
            amqp_message_received = False
            # start amqp thread
            td = fit_amqp.AMQP_worker(exchange_name = "on.events", routing_key="node.removed.#",
                                      externalcallback = amqpcallback, timeout = 10)
            td.setDaemon(True)
            td.start()
            mon_url = '/api/2.0/nodes/{}'.format(rack)
            mon_data = fit_common.rackhdapi(mon_url, action = 'delete')
            self.assertIn(mon_data['status'], range(200,205), "Incorrect HTTP return code: {}".format(mon_data['status']))
            timecount = 0
            while amqp_message_received is False and timecount<10:
                sleep(1)
                timecount = timecount + 1
            self.assertNotEquals(timecount, 10, "No AMQP message received")
            expectedkey="node.removed.information." + rack + '.' + rack
            expectedpayload={"type": "node", "action": "removed", "typeId":rack,
                             "nodeId": rack, "severity": "information", "version": "1.0",
                             "createdAt": mon_data['headers']['Date']}
            self.assertEquals(self.compare_message(expectedkey, expectedpayload), True, "AMQP Message Check Error!")


if __name__ == '__main__':
    fit_common.unittest.main()
