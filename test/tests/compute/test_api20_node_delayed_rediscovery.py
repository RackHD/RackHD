'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This script tests node delayed rediscovery.
This test takes 10 minutes to run and runs against a single node, random or
specified via nodeid. Delayed rediscovery will start and script will send command to reboot the
node. The test will check to see the catalogs get refreshed after the rediscovery.

example:
python run_tests.py -stack 4 -test tests/compute/test_api20_node_delayed_rediscovery.py [-nodeid <nodeid>]

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

log = flogging.get_loggers()


def random_user_generator(pre_user):
    # The test will inject a random user name into the nodes BMC data.
    # This value is used to check that the catalog data gets updated
    # after rediscovery.

    user = ''.join(random.choice(string.lowercase) for i in range(10))
    count = 0
    while (user == pre_user):
        user = ''.join(random.choice(string.lowercase) for i in range(10))
        count = count + 1
        if count == 10:
            return None
    return user


def wait_for_workflow_complete(instanceid, start_time, wait_time=2700, cycle=30):
    # This routine polls a workflow task ID for completion

    log.info(" Workflow started at time: %s", str(time.asctime()))

    while time.time() - start_time < wait_time:  # limit test to waittime seconds
        result = fit_common.rackhdapi("/api/2.0/workflows/" + instanceid)
        status = result['json']['status']
        injectableName = result['json']['injectableName']

        if result['status'] != 200:
            log.error("HTTP error: %s", result['text'])
            return False
        if status in ['running', 'pending']:
            log.info(" %s workflow status: %s", injectableName, status)
            fit_common.time.sleep(cycle)
        elif status == 'succeeded':
            log.info(" %s workflow status: %s", injectableName, status)
            log.info(" Workflow completed at time: %s", str(time.asctime()))
            return True
        else:
            error = result['text']
            log.error(" Workflow failed: status: %s text: %s", status, error)
            return False

    log.error("Workflow Timeout: %s", result['text'])
    return False


def get_ipmi_user(self, nodeid):
    # Get the IPMI user for node

    result = fit_common.rackhdapi('/api/2.0/nodes/' + nodeid + '/catalogs/ipmi-user-list-1', action='get')
    self.assertEqual(result['status'], 200, msg="IPMI user list catalog could not be retrieved.")
    self.assertGreater(len(result['json']), 0, msg=("Node %s IPMI user catalog has 0 length" % nodeid))

    try:
        ipmi_user = result['json']['data']['6']['']
    except KeyError:
        try:
            ipmi_user = result['json']['data']['6']['admin']
        except KeyError:
            ipmi_user = None

    return ipmi_user


@attr(all=False, regression=False, smoke=False, refresh_group=True)
class api20_node_rediscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # class method run once per script

        # default base payload for Rediscovery Graph
        cls.__payload = {
            "name": "Graph.Refresh.Delayed.Discovery",
            "options": {
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

        # Get the list of nodes
        nodelist = fit_common.node_select(no_unknown_nodes=True)

        assert (len(nodelist) != 0), "No valid nodes discovered"

        # Select one node at random
        cls.__nodeid = nodelist[random.randint(0, len(nodelist) - 1)]

        # Delete active workflows for specified node
        fit_common.cancel_active_workflows(cls.__nodeid)
        cls.__previous_ipmi_user = None

    def setUp(self):
        # test method runs at the start of each test

        self.__nodeid = self.__class__.__nodeid
        self.__payload = self.__class__.__payload
        self.__previous_ipmi_user = self.__class__.__previous_ipmi_user

    def test01_node_check(self):
        # Get node data
        node = fit_common.rackhdapi('/api/2.0/nodes/' + self.__nodeid)['json']
        nodesku = fit_common.rackhdapi(node.get('sku'))['json']['name']
        log.info(" Node ID: %s", self.__nodeid)
        log.info(" Node SKU: %s ", nodesku)
        log.info(" Graph Name: %s", self.__payload['name'])

        # Ensure the compute node is powered on and reachable
        result = fit_common.rackhdapi('/api/2.0/nodes/' + self.__nodeid + '/workflows', action='post',
                                      payload={"name": "Graph.PowerOn.Node"})
        self.assertEqual(result['status'], 201, msg="Node Power on workflow API failed, see logs.")
        instanceId = result['json']['instanceId']
        self.assertTrue(wait_for_workflow_complete(instanceId, time.time(), 50, 5),
                        msg="Node Power on workflow failed, see logs.")

    @depends(after=test01_node_check)
    def test02_create_node_user(self):
        # Get previous IPMI user from RackHD node catalog
        self.__previous_ipmi_user = get_ipmi_user(self, self.__nodeid)

        # Set new IPMI user on node
        user = random_user_generator(self.__previous_ipmi_user)
        self.assertNotEqual(user, None, msg="Error generating IPMI username")
        command = "user set name 6 " + user
        result = test_api_utils.run_ipmi_command_to_node(self.__nodeid, command)
        self.assertEqual(result['exitcode'], 0, msg="Error setting node username")

    @depends(after=test02_create_node_user)
    def test03_refresh_delayed(self):
        # Execute delayed rediscovery which refreshes the node catalog

        temp_payload = dumps(self.__payload)
        workflow_payload = loads(temp_payload.replace("NODEID", self.__nodeid))
        log.debug(" Payload: %s", workflow_payload)

        result = fit_common.rackhdapi('/api/2.0/workflows', action='post', payload=workflow_payload)

        self.assertEqual(result['status'], 201,
                         msg='Was expecting code 201. Got ' + str(result['status']))

        graphId = result['json']['context']['graphId']

        # Send command to reboot node
        command = "chassis power reset"
        result = test_api_utils.run_ipmi_command_to_node(self.__nodeid, command)
        self.assertEqual(result['exitcode'], 0, msg="Error rebooting node")

        self.assertTrue(wait_for_workflow_complete(graphId, time.time()), "Delayed rediscovery workflow failed")

    @depends(after=test03_refresh_delayed)
    def test04_verify_rediscovery(self):

        # get the Ipmi user catalog for node
        new_ipmi_user = get_ipmi_user(self, self.__nodeid)

        self.assertNotEqual(new_ipmi_user, None, msg="IPMI user didn't get created or cataloged correctly")
        self.assertNotEqual(new_ipmi_user, self.__previous_ipmi_user, msg="IPMI user didn't change after rediscovery")


if __name__ == '__main__':
    fit_common.unittest.main()
