'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This script tests node rediscovery.
This test takes TBD minutes to run.


python run_tests.py -stack 4 -test tests/compute/test_api20_node_rediscovery.py

'''

import fit_path  # NOQA: unused import
import fit_common
import flogging
import random
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

# if an external payload file is specified, use that
#payload = fit_common.fitcfg().get('bootstrap-payload', None)
#if payload:
#    PAYLOAD = payload


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


# ------------------------ Tests -------------------------------------


#@attr(all=False)
@attr(all=False, regression=False, smoke=False) # TODO add attr refresh= True
class api20_node_rediscovery(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # class method is run once per script
        # usually not required in the script
        self.__client = config.api_client
        self.__dmi_catalog = {}
        self.__bmc_catalog = {}

        # Get the list of nodes
        nodelist = []

        api_data = fit_common.rackhdapi('/api/2.0/nodes')

        try:
            nodes = api_data.get('json')
        except:
            self.fail("No Json data in repsonse")
        for node in nodes:
            nodetype = node['type']
            if nodetype == "compute":
                nodeid = node['id']
                nodename = test_api_utils.get_rackhd_nodetype(nodeid)
                if not nodename == "Unidentified-Compute":
                    print nodename
                    nodelist.append(nodeid)

        # TODO: FIXME
        assert (len(nodelist) !=0) , "No valid nodes discovered"

        # Select one node at random
        self.__NODE = nodelist[random.randint(0, len(nodelist) - 1)]

        print "****** self.__NODE"
        print self.__NODE

        # delete active workflows for specified node
        fit_common.cancel_active_workflows(self.__NODE)

    def test01_node_check(self):
        # Log node data

        print "****** self.__NODE 2"
        print self.__NODE

        nodeinfo = fit_common.rackhdapi('/api/2.0/nodes/' + self.__NODE)['json']
        nodesku = fit_common.rackhdapi(nodeinfo.get('sku'))['json']['name']
        log.info(" Node ID: " + self.__NODE)
        log.info(" Node SKU: " + nodesku)
        log.info(" Graph Name: " + PAYLOAD['name'])

        # Ensure the compute node is powered on and reachable
        result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                      self.__NODE +
                                      '/workflows',
                                      action='post', payload={"name": "Graph.PowerOn.Node"})
        self.assertEqual(result['status'], 201, "Node Power on workflow API failed, see logs.")
        self.assertTrue(wait_for_workflow_complete(result['json']['instanceId'], time.time(), 50, 5),
                        "Node Power on workflow failed, see logs.")

    @depends(after=test01_node_check)
    def test02_get_catalogs(self):


        print "****** self.__NODE 3"
        print self.__NODE

        # get the dmi catalog for node and fill in mock sku
        Api().nodes_get_catalog_source_by_id(identifier=self.__NODE, source='dmi')
        self.__dmi_catalog = loads(self.__client.last_response.data)
        self.assertGreater(len(self.__dmi_catalog), 0, msg=("Node %s dmi catalog has zero length" % self.__NODE))
        print "**** Node Catalog DMI ****"
        print self.__dmi_catalog

        # get the bmc catalog for node and fill in mock sku
        Api().nodes_get_catalog_source_by_id(identifier=self.__NODE, source='bmc')
        self.__bmc_catalog = loads(self.__client.last_response.data)
        self.assertGreater(len(self.__bmc_catalog), 0, msg=("Node %s bmc catalog has zero length" % self.__NODE))
        print "**** Node Catalog BMC ****"
        print self.__bmc_catalog


    @depends(after=test02_get_catalogs)
    def test03_refresh_immediate(self):

        global PAYLOAD

        print "****** self.__NODE 4"
        print self.__NODE


        payload_string = dumps(PAYLOAD)
        PAYLOAD =  loads(payload_string.replace("NODEID", self.__NODE))
        print PAYLOAD

        result = fit_common.rackhdapi('/api/2.0/workflows', action='post', payload=PAYLOAD)

        self.assertEqual(result['status'], 201,
                         'Was expecting code 201. Got ' + str(result['status']))

        graphId = result['json']['context']['graphId']
        
        retries = 240
        for dummy in range(0, retries):
            result = fit_common.rackhdapi('/api/2.0/workflows/' + graphId, action='get')
            if result['json']['status'] == 'running' or result['json']['status'] == 'Running':
                if fit_common.VERBOSITY >= 2:
                    # Add print out of workflow
                    #print 'Graph name="{0}"; Graph state="{1}"'.format(result['json']['tasks'][0]['label'], result['json']['status'])
                    print 'GraphID ="{0}"; Status="{1}"'.format(graphId, result['json']['status'])
                fit_common.time.sleep(10)
            elif result['json']['status'] == 'succeeded':
                if fit_common.VERBOSITY >= 2:
                    print "Workflow state: {}".format(result['json']['status'])
                break
            else:
                if fit_common.VERBOSITY >= 2:
                    print "Workflow state (unknown): {}".format(result['json']['status'])
                break

        print "Graph finished  with the following state: " + result['json']['status']


        self.assertEqual(result['json']['status'], 'succeeded',
                         'Was expecting succeeded. Got ' + result['json']['status'])



#        # launch workflow
#        workflowid = None
#        result = fit_common.rackhdapi('/api/2.0/nodes/' +
#                                      self.__NODE +
#                                      '/workflows',
#                                      action='post', payload=PAYLOAD)
#       if result['status'] == 201:
#           # workflow running
#           log.info_5(" InstanceID: " + result['json']['instanceId'])
#           log.info_5(" Payload: " + fit_common.json.dumps(PAYLOAD))
#           workflowid = result['json']['instanceId']
#       else:
#           # workflow failed with response code
#           log.error(" InstanceID: " + result['text'])
#           log.error(" Payload: " + fit_common.json.dumps(PAYLOAD))
#           self.fail("Workflow failed with response code: " + result['status'])
#       self.assertTrue(wait_for_workflow_complete(workflowid, time.time()), "OS Install workflow failed, see logs.")
#

if __name__ == '__main__':
    fit_common.unittest.main()
