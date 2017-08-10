'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This script tests arbitrary payload of the RackHD API 2.0 OS bootstrap workflows.
The default case is running a minimum payload ESXi 6.0 OS install.
Other ESXi OS install cases can be specified by creating a payload file and specifiying it using the '-extra' argument.
This test takes 15-20 minutes to run.

Example payload file (installed in configuration dir):

{"bootstrap-payload":
    {"name": "Graph.InstallESXi",
        "options": {"defaults": {
        "version": "6",
        "repo": "http://172.31.128.1:8080/ESXi/6.0",
        "rootPassword": "1234567",
        "hostname": "rackhdnode",
        "users": [{"name": "rackhduser",
                   "password": "RackHDRocks!",
                   "uid": 1010}]}}}
}

Example command line using external payload file:

python run_tests.py -stack 4 -test tests/bootstrap/test_api20_esxi_bootstrap.py -extra base_esxi_55_install.json

'''

import fit_path  # NOQA: unused import
from nose.plugins.attrib import attr
import fit_common
import flogging
import json
import random
import time
from datetime import datetime
from nosedep import depends
log = flogging.get_loggers()

# sample default base payload
PAYLOAD = {"name": "Graph.InstallESXi",
           "options": {"defaults": {"version": "6",
                                    "repo": "http://172.31.128.1:8080/ESXi/6.0",
                                    "rootPassword": "1234567",
                                    "hostname": "rackhdnode",
                                    "users": [{"name": "rackhduser",
                                               "password": "RackHDRocks!",
                                               "uid": 1010}]}}}
# if an external payload file is specified, use that
config = fit_common.fitcfg().get('bootstrap-payload', None)
if config:
    PAYLOAD = config


# function to return the value of a field from the workflow response
def findall(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                log.error(" workflow error: %s", v)
            findall(v, key)
    elif isinstance(obj, list):
        for item in obj:
            findall(item, key)
    else:
        pass


# this routine polls a workflow task ID for completion
def wait_for_workflow_complete(instanceid, start_time, waittime=7200, cycle=30):
    log.info_1(" Workflow started at time: " + str(datetime.fromtimestamp(start_time)))
    while time.time() - start_time < waittime:  # limit test to waittime seconds
        result = fit_common.rackhdapi("/api/2.0/workflows/" + instanceid)
        if result['status'] != 200:
            log.error(" HTTP error: " + result['text'])
            return False
        if result['json']['status'] in ['running', 'pending']:
            log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            fit_common.time.sleep(cycle)
        elif result['json']['status'] == 'succeeded':
            log.info_1("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            end_time = time.time()
            log.info_1(" Workflow completed at time: " + str(datetime.fromtimestamp(end_time)))
            log.info_1(" Workflow duration: " + str(end_time - start_time))
            return True
        else:
            end_time = time.time()
            log.info_1(" Workflow failed at time: " + str(datetime.fromtimestamp(end_time)))
            log.info_1(" Workflow duration: " + str(end_time - start_time))
            try:
                res = json.loads(result['text'])
                findall(res, "error")
            except:
                res = result['text']
            log.error(" Workflow failed: status: %s", result['json']['status'])
            log.error(" Data: %s", json.dumps(res, indent=4, separators=(',', ':')))
            return False
    try:
        res = json.loads(result['text'])
    except:
        res = result['text']
    log.error(" Workflow Timeout: " + json.dumps(res, indent=4, separators=(',', ':')))
    return False


# ------------------------ Tests -------------------------------------


@attr(all=False)
class api20_bootstrap_esxi(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the list of nodes
        NODECATALOG = fit_common.node_select()
        assert (len(NODECATALOG) != 0), "There are no nodes currently discovered"

        # Select one node at random
        cls.__NODE = NODECATALOG[random.randint(0, len(NODECATALOG) - 1)]

        # Print node Id, node BMC mac ,node type
        nodeinfo = fit_common.rackhdapi('/api/2.0/nodes/' + cls.__NODE)['json']
        nodesku = fit_common.rackhdapi(nodeinfo.get('sku'))['json']['name']
        monurl = "/api/2.0/nodes/" + cls.__NODE + "/catalogs/bmc"
        mondata = fit_common.rackhdapi(monurl, action="get")
        catalog = mondata['json']
        bmcresult = mondata['status']
        if bmcresult != 200:
            log.info_1(" Node ID: " + cls.__NODE)
            log.info_1(" Error on catalog/bmc command")
        else:
            log.info_1(" Node ID: " + cls.__NODE)
            log.info_1(" Node SKU: " + nodesku)
            log.info_1(" Node BMC Mac: %s", catalog.get('data')['MAC Address'])
            log.info_1(" Node BMC IP Addr: %s", catalog.get('data')['IP Address'])
            log.info_1(" Node BMC IP Addr Src: %s", catalog.get('data')['IP Address Source'])

        # delete active workflows for specified node
        result = fit_common.cancel_active_workflows(cls.__NODE)
        assert (result is True), "There are still some active workflows running against the node"

    def test01_node_check(self):
        # Log node data
        nodeinfo = fit_common.rackhdapi('/api/2.0/nodes/' + self.__class__.__NODE)['json']
        nodesku = fit_common.rackhdapi(nodeinfo.get('sku'))['json']['name']
        log.info_1(" Node ID: " + self.__class__.__NODE)
        log.info_1(" Node SKU: " + nodesku)
        log.info_1(" Graph Name: Graph.PowerOn.Node")

        # Ensure the compute node is powered on and reachable
        result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                      self.__class__.__NODE +
                                      '/workflows',
                                      action='post', payload={"name": "Graph.PowerOn.Node"})
        self.assertEqual(result['status'], 201, "Node Power on workflow API failed, see logs.")
        self.assertTrue(wait_for_workflow_complete(result['json']['instanceId'], time.time(), 50, 5),
                        "Node Power on workflow failed, see logs.")

    @depends(after=test01_node_check)
    def test02_os_install(self):
        # Log node data
        nodeinfo = fit_common.rackhdapi('/api/2.0/nodes/' + self.__class__.__NODE)['json']
        nodesku = fit_common.rackhdapi(nodeinfo.get('sku'))['json']['name']
        log.info_1(" Node ID: " + self.__class__.__NODE)
        log.info_1(" Node SKU: " + nodesku)
        log.info_1(" Graph Name: Graph.InstallESXi")
        log.info_1(" Payload: " + fit_common.json.dumps(PAYLOAD))

        # launch workflow
        workflowid = None
        result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                      self.__class__.__NODE +
                                      '/workflows',
                                      action='post', payload=PAYLOAD)
        if result['status'] == 201:
            # workflow running
            log.info_1(" InstanceID: " + result['json']['instanceId'])
            workflowid = result['json']['instanceId']
        else:
            # workflow failed with response code
            log.error(" InstanceID: " + result['text'])
            self.fail("Workflow failed with response code: " + result['status'])
        self.assertTrue(wait_for_workflow_complete(workflowid, time.time()), "OS Install workflow failed, see logs.")


if __name__ == '__main__':
    fit_common.unittest.main()
