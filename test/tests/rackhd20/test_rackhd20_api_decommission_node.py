'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''

import fit_path  # NOQA: unused import
import random
import time
import flogging
from nose.plugins.attrib import attr
from common import fit_common
from json import dumps
from nosedep import depends

# set up the logging
log = flogging.get_loggers()

# Local methods
NODECATALOG = fit_common.node_select()


# Decommission base payload
DECOMMISSION_PAYLOAD = {
    "name": "Graph.Bootstrap.Decommission.Node",
    "options": {
        "defaults": {
        }
    }
}

# validate base payload
VALIDATE_PAYLOAD = {
    "name": "Graph.Bootstrap.Decommission.Node.Test",
    "options": {
        "defaults": {
        }
    }
}


@attr(regression=True, smoke=False)
class rackhd20_api_workflows(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the list of nodes
        NODECATALOG = fit_common.node_select()
        # Select one node at random
        cls.__NODE = NODECATALOG[random.randint(0, len(NODECATALOG) - 1)]
        # delete active workflows for specified node
        fit_common.cancel_active_workflows(cls.__NODE)

    # this routine polls a workflow task ID for completion
    def __wait_for_workflow_complete(self, instanceid, start_time, waittime=900, cycle=30):
        log.info_5(" Workflow started at time: %f", start_time)
        while time.time() - start_time < waittime:
            result = fit_common.rackhdapi("/api/2.0/workflows/" + instanceid)
            if result['status'] != 200:
                log.error(" HTTP error: " + result['text'])
                return False
            if result['json']['status'] in ['running', 'pending']:
                log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
                time.sleep(cycle)
            elif result['json']['status'] == 'succeeded':
                log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
                log.info_5(" Workflow completed at time: " + str(time.time()))
                return True
            else:
                log.error(" Workflow failed: status: %s text: %s", result['json']['status'], result['text'])
                return False
        log.error(" Workflow Timeout: " + result['text'])
        return False

    def test01_decommission_node(self):
        # launch workflow
        workflowid = None
        result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                      self.__class__.__NODE +
                                      '/workflows',
                                      action='post', payload=DECOMMISSION_PAYLOAD)
        if result['status'] == 201:
            # workflow running
            log.info_5(" InstanceID: " + result['json']['instanceId'])
            log.info_5(" Payload: " + dumps(DECOMMISSION_PAYLOAD))
            workflowid = result['json']['instanceId']
        else:
            # workflow failed with response code
            log.error(" InstanceID: " + result['text'])
            log.error(" Payload: " + dumps(DECOMMISSION_PAYLOAD))
            self.fail("Workflow failed with response code: " + result['status'])
        self.assertTrue(self.__wait_for_workflow_complete(workflowid, time.time()),
                        "Decommission Node workflow failed, see logs.")

    @depends(after=test01_decommission_node)
    def test02_validate_decommissioned_node(self):
        # launch workflow
        workflowid = None
        result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                      self.__class__.__NODE +
                                      '/workflows',
                                      action='post', payload=VALIDATE_PAYLOAD)
        if result['status'] == 201:
            # workflow running
            log.info_5(" InstanceID: " + result['json']['instanceId'])
            log.info_5(" Payload: " + dumps(VALIDATE_PAYLOAD))
            workflowid = result['json']['instanceId']
        else:
            # workflow failed with response code
            log.error(" InstanceID: " + result['text'])
            log.error(" Payload: " + dumps(VALIDATE_PAYLOAD))
            self.fail("Workflow failed with response code: {}".format(result['status']))
        self.assertTrue(self.__wait_for_workflow_complete(workflowid, time.time()),
                        "Validation Decommissioned Node workflow failed, see logs.")


if __name__ == '__main__':
    fit_common.unittest.main()
