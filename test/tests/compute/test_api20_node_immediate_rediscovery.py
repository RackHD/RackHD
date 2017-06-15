'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This script tests node immediate rediscovery.
This test takes TBD minutes to run.


python run_tests.py -stack 4 -test tests/compute/test_api20_node_immediate_rediscovery.py [-nodeid <nodeid>]

'''

import fit_path  # NOQA: unused import
import fit_common
import flogging
import random
import string
import test_api_utils
import time
import unittest

from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr
from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException

log = flogging.get_loggers()

def random_user_generator(pre_user):
    random_user = ''.join(random.choice(string.lowercase) for i in range(10))
    while (random_user == pre_user):
        random_user = ''.join(random.choice(string.lowercase) for i in range(10))
    return random_user 
    

# default base payload
PAYLOAD =  {
  "name": "Graph.Refresh.Immediate.Discovery",
   "options": {
        "reset-at-start": {
            "nodeId": "NODEID"
        },
        "discovery-refresh-graph": {
            "graphOptions": {
                "target": "NODEID"
            },
            "nodeId": "NODEID"
        },
        "generate-sku": {
            "nodeId": "NODEID"
        },
        "generate-enclosure": {
            "nodeId": "NODEID"
        },
        "create-default-pollers": {
            "nodeId": "NODEID"
        },
        "run-sku-graph": {
            "nodeId": "NODEID"
        },
        "nodeId": "NODEID"
   } 
}

# this routine polls a workflow task ID for completion
def wait_for_workflow_complete(instanceid, start_time, waittime=2700, cycle=30):
    log.info(" Workflow started at time: " + str(start_time))
    while time.time() - start_time < waittime:  # limit test to waittime seconds
        result = fit_common.rackhdapi("/api/2.0/workflows/" + instanceid)
        if result['status'] != 200:
            log.error(" HTTP error: " + result['text'])
            return False
        if result['json']['status'] in ['running', 'pending']:
            log.info("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            fit_common.time.sleep(cycle)
        elif result['json']['status'] == 'succeeded':
            log.info("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            log.info(" Workflow completed at time: " + str(time.time()))
            return True
        else:
            log.error(" Workflow failed: status: %s text: %s", result['json']['status'], result['text'])
            return False
    log.error(" Workflow Timeout: " + result['text'])
    return False

# Get IPMI user
def get_ipmi_user(self, nodeid):

    # get the previous IPMI user for node
    result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                  nodeid +
                                  '/catalogs/ipmi-user-list-1',
                                  action='get')
    self.assertEqual(result['status'], 200, msg="IPMI user list catalog could not be retrieved.")
    catalog = result['json']

    self.assertGreater(len(catalog), 0, msg=("Node %s previous IPMI user catalog has zero length" % nodeid))

    try:
        ipmi_user = catalog['data']['6']['']
    except KeyError:
        try:
            ipmi_user = catalog['data']['6']['admin']
        except KeyError:
            ipmi_user = None

    return ipmi_user



# ------------------------ Tests -------------------------------------


#@attr(all=False)
@attr(all=False, regression=False, smoke=False, refresh_group=True)
class api20_node_rediscovery(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # class method is run once per script
        # usually not required in the script
        cls.__client = config.api_client

        # Get the list of nodes
        nodelist = fit_common.node_select(no_unknown_nodes=True)

        assert ((len(nodelist) !=0) , "No valid nodes discovered")

        # Select one node at random
        cls.__nodeid = nodelist[random.randint(0, len(nodelist) - 1)]

        # delete active workflows for specified node
        fit_common.cancel_active_workflows(cls.__nodeid)

        cls.__previous_ipmi_user = None


    def setUp(self):
        self.__nodeid = self.__class__.__nodeid
        self.__client = self.__class__.__client 
        self.__previous_ipmi_user = self.__class__.__previous_ipmi_user

    def test01_node_check(self):

        # Log node data
        nodeinfo = fit_common.rackhdapi('/api/2.0/nodes/' + self.__nodeid)['json']
        nodesku = fit_common.rackhdapi(nodeinfo.get('sku'))['json']['name']
        log.info(" Node ID: " + self.__nodeid)
        log.info(" Node SKU: " + nodesku)
        log.info(" Graph Name: " + PAYLOAD['name'])

        # Ensure the compute node is powered on and reachable
        result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                      self.__nodeid +
                                      '/workflows',
                                      action='post', payload={"name": "Graph.PowerOn.Node"})
        self.assertEqual(result['status'], 201, msg="Node Power on workflow API failed, see logs.")
        self.assertTrue(wait_for_workflow_complete(result['json']['instanceId'], time.time(), 50, 5),
                        msg="Node Power on workflow failed, see logs.")

    @depends(after=test01_node_check)
    def test02_get_previous_ipmi_user(self):
        # Get previous IPMI user
        self.__previous_ipmi_user = get_ipmi_user(self, self.__nodeid)

    @depends(after=test02_get_previous_ipmi_user)
    def test03_create_node_user(self):
        command = "user set name 6 " + random_user_generator(self.__previous_ipmi_user)
        result = test_api_utils.run_ipmi_command_to_node(self.__nodeid, command)
        self.assertEqual (result['exitcode'], 0, msg="Error setting node username")


    @depends(after=test03_create_node_user)
    def test04_refresh_immediate(self):

        global PAYLOAD

        payload_string = dumps(PAYLOAD)
        PAYLOAD =  loads(payload_string.replace("NODEID", self.__nodeid))
        print PAYLOAD

        result = fit_common.rackhdapi('/api/2.0/workflows', action='post', payload=PAYLOAD)

        self.assertEqual(result['status'], 201,
                         msg='Was expecting code 201. Got ' + str(result['status']))

        graphId = result['json']['context']['graphId']

        self.assertTrue(wait_for_workflow_complete(graphId, time.time()), "Immediate rediscovery workflow failed")

    @depends(after=test04_refresh_immediate)
    def test05_verify_rediscovery(self):

        # get the Ipmi user catalog for node 
        new_ipmi_user = get_ipmi_user(self, self.__nodeid)

        self.assertNotEqual(new_ipmi_user, None, msg="IPMI user didn't get created or cataloged correctly")
        self.assertNotEqual(new_ipmi_user, self.__previous_ipmi_user, msg="IPMI user didn't change")


if __name__ == '__main__':
    fit_common.unittest.main()
