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
@attr(all=False, regression=False, smoke=False, refresh_group=True)
class api20_node_rediscovery(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(self):
        # class method is run once per script
        # usually not required in the script
        self.__client = config.api_client
        self.__pre_catalog = {}
        self.__post_catalog = {}

        # Get the list of nodes
        nodelist = fit_common.node_select(no_unknown_nodes=True)
        print "**** nodelist  = " 
        print  nodelist

        for nodeid in nodelist:
            print "**** nodeid  = " 
            print  nodeid
            node_data = fit_common.rackhdapi('/api/2.0/nodes/' + nodeid)
            print "**** node data  = " 
            print  node_data
            
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
    def test02_get_pre_catalog(self):

        # get the IPMI user catalog for node 
        Api().nodes_get_catalog_source_by_id(identifier=self.__NODE, source='ipmi-user-list-1')
        self.__pre_catalog = loads(self.__client.last_response.data)
        self.assertGreater(len(self.__pre_catalog), 0, msg=("Node %s pre IPMI user catalog has zero length" % self.__NODE))
        print "**** Pre Node Catalog IPMI user ****"
        print self.__pre_catalog

    @depends(after=test02_get_pre_catalog)
    def test03_get_obm_credential(self):
        log.info("**** Get OBM credential")
        usr = ""
        pwd = ""

        # find correct BMC passwords from credentials list
        for creds in fit_common.fitcreds()['bmc']:
            print "****** Creds*******"
            print creds
            if fit_common.remote_shell('ipmitool -I lanplus -H ' + fit_common.fitcfg()['bmc'] +
                                       ' -U ' + creds['username'] + ' -P ' +
                                       creds['password'] + ' fru')['exitcode'] == 0:
                usr = creds['username']
                pwd = creds['password'] 

    @depends(after=test03_get_obm_credential)
    def test04_refresh_immediate(self):

        global PAYLOAD

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

    @depends(after=test04_refresh_immediate)
    def test05_get_post_catalog(self):

        # get the Ipmi user catalog for node 
        Api().nodes_get_catalog_source_by_id(identifier=self.__NODE, source='ipmi-user-list-1')
        self.__post_catalog = loads(self.__client.last_response.data)
        self.assertGreater(len(self.__post_catalog), 0, msg=("Node %s post ipmi user catalog has zero length" % self.__NODE))
        print "**** Post Node Catalog IMPI User ****"
        print self.__post_catalog




if __name__ == '__main__':
    fit_common.unittest.main()
