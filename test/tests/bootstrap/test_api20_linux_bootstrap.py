'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This script tests arbitrary payload of the RackHD API 2.0 OS bootstrap workflows.
The default case is running a minimum payload CentOS 7 OS install.
Other Linux-type OS install cases can be specified by creating a payload file and specifiying it using the '-extra' argument.
This test takes 15-20 minutes to run.

Example payload file (installed in configuration dir):

{"bootstrap-payload":
    {"name": "Graph.InstallRHEL",
        "options": {"defaults": {
        "version": "7",
        "repo": "http://172.31.128.1:8080/RHEL/7.0",
        "rootPassword": "1234567",
        "hostname": "rackhdnode",
        "users": [{"name": "rackhduser",
                   "password": "RackHDRocks!",
                   "uid": 1010}]}}}
}

Example command line using external payload file:

python run_tests.py -stack 4 -test tests/bootstrap/test_api20_linux_bootstrap.py -extra base_redhat_7_install.json

'''

import fit_path  # NOQA: unused import
from nose.plugins.attrib import attr
import fit_common
import flogging
import random
import time
from nosedep import depends
log = flogging.get_loggers()

# sample default base payload
PAYLOAD = {"name": "Graph.InstallCentOS",
           "options": {"defaults": {"version": "7",
                                    "repo": "http://172.31.128.1:8080/CentOS/7.0",
                                    "rootPassword": "1234567",
                                    "hostname": "rackhdnode",
                                    "users": [{"name": "rackhduser",
                                               "password": "RackHDRocks!",
                                               "uid": 1010}]}}}
# if an external payload file is specified, use that
config = fit_common.fitcfg().get('bootstrap-payload', None)
if config:
    PAYLOAD = config


# this routine polls a workflow task ID for completion
def wait_for_workflow_complete(instanceid, start_time, waittime=1800, cycle=30):
    log.info_5(" Workflow started at time: " + str(start_time))
    while time.time() - start_time < waittime:  # limit test to waittime seconds
        result = fit_common.rackhdapi("/api/2.0/workflows/" + instanceid)
        if result['status'] != 200:
            log.error(" HTTP error: " + result['text'])
            return False
        if result['json']['status'] in ['running', 'pending']:
            log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            fit_common.time.sleep(cycle)
        elif result['json']['status'] == 'succeeded':
            log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            log.info_5(" Workflow completed at time: " + str(time.time()))
            return True
        else:
            log.error(" Workflow failed: status: %s text: %s", result['json']['status'], result['text'])
            return False
    log.error(" Workflow Timeout: " + result['text'])
    return False


# ------------------------ Tests -------------------------------------


@attr(all=False)
class api20_bootstrap_linux(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the list of nodes
        NODECATALOG = fit_common.node_select()
        # Select one node at random
        cls.__NODE = NODECATALOG[random.randint(0, len(NODECATALOG) - 1)]
        # delete active workflows for specified node
        fit_common.cancel_active_workflows(cls.__NODE)

    def test01_node_check(self):
        # Log node data
        nodeinfo = fit_common.rackhdapi('/api/2.0/nodes/' + self.__class__.__NODE)['json']
        nodesku = fit_common.rackhdapi(nodeinfo.get('sku'))['json']['name']
        log.info_5(" Node ID: " + self.__class__.__NODE)
        log.info_5(" Node SKU: " + nodesku)
        log.info_5(" Graph Name: " + PAYLOAD['name'])

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
        # launch workflow
        workflowid = None
        result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                      self.__class__.__NODE +
                                      '/workflows',
                                      action='post', payload=PAYLOAD)
        if result['status'] == 201:
            # workflow running
            log.info_5(" InstanceID: " + result['json']['instanceId'])
            log.info_5(" Payload: " + fit_common.json.dumps(PAYLOAD))
            workflowid = result['json']['instanceId']
        else:
            # workflow failed with response code
            log.error(" InstanceID: " + result['text'])
            log.error(" Payload: " + fit_common.json.dumps(PAYLOAD))
            self.fail("Workflow failed with response code: " + result['status'])
        self.assertTrue(wait_for_workflow_complete(workflowid, time.time()), "OS Install workflow failed, see logs.")


if __name__ == '__main__':
    fit_common.unittest.main()
