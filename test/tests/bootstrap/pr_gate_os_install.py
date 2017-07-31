'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.


'''

import fit_path  # NOQA: unused import
from nose.plugins.attrib import attr
import fit_common
import flogging
import sys
log = flogging.get_loggers()

# This gets the list of nodes
NODECATALOG = fit_common.node_select()

# dict containing bootstrap workflow IDs and states
NODE_STATUS = {}

# global timer
START_TIME = fit_common.time.time()

# OS install info

OSLIST = [{"workflow": "Graph.InstallESXi", "version": "6.0", "path": "/repo/esxi/6.0", "kvm": False},
          {"workflow": "Graph.InstallUbuntu", "version": "trusty", "path": "/repo/ubuntu", "kvm": False},
          {"workflow": "Graph.InstallCentOS", "version": "6.5", "path": "/repo/centos/6.5", "kvm": False}]

# download RackHD config from host
rackhdresult = fit_common.rackhdapi('/api/2.0/config')
if rackhdresult['status'] != 200:
    log.error(" Unable to contact host, exiting. ")
    sys.exit(255)
rackhdconfig = rackhdresult['json']
rackhdhost = "http://" + str(rackhdconfig['apiServerAddress']) + ":" + str(rackhdconfig['apiServerPort'])


# this routine polls a workflow task ID for completion
def wait_for_workflow_complete(taskid):
    result = None
    while fit_common.time.time() - START_TIME < 1800 or result is None:  # limit test to 30 minutes
        result = fit_common.rackhdapi("/api/2.0/workflows/" + taskid)
        if result['status'] != 200:
            log.error(" HTTP error: %s", result['text'])
            return False
        wf_name = result['json']['injectableName']
        if result['json']['status'] == 'running' or result['json']['status'] == 'pending':
            log.info_5(" %s Workflow status: %s", wf_name, result['json']['status'])
            fit_common.time.sleep(30)
        elif result['json']['status'] == 'succeeded':
            log.info_5(" %s Workflow status: %s", wf_name, result['json']['status'])
            # Cheat for status in Jenkins
            print("{} Workflow status: {}".format(wf_name, result['json']['status']))
            return True
        else:
            log.error(" %s Workflow failed: %s", wf_name, result['text'])
            return False
    log.error(" %s Workflow Timeout: %s", wf_name, result['text'])
    return False


# helper routine to return the task ID associated with the running bootstrap workflow
def node_taskid(workflow, version, kvm):
    for entry in NODE_STATUS:
        if NODE_STATUS[entry]['workflow'] == workflow \
                and str(version) in NODE_STATUS[entry]['version'] \
                and NODE_STATUS[entry]['kvm'] == kvm:
            return NODE_STATUS[entry]['id']
    return ""


# helper routine to dispaly task status info to the user at the end of each test
def display_workflow_info(taskid):
    for node in NODE_STATUS:
        if taskid == NODE_STATUS[node]['id']:
            result = fit_common.rackhdapi("/api/2.0/workflows/" + taskid)
            if result['status'] != 200:
                log.error(" HTTP error: %s, cannot print results", result['text'])
                return
            NODE_STATUS[node]['EndTime'] = fit_common.time.time()
            log.info(" Node: %s", fit_common.json.dumps(NODE_STATUS[node], indent=4))
            print("Node info {}".format(fit_common.json.dumps(NODE_STATUS[node], indent=4)))


# Match up tests to node IDs to feed skip decorators
index = 0  # node index
for item in OSLIST:
    if index < len(NODECATALOG):
        NODE_STATUS[NODECATALOG[index]] = \
            {"workflow": item['workflow'], "version": item['version'], "kvm": item['kvm'], "id": "Pending"}
    index += 1

# ------------------------ Tests -------------------------------------


@attr(all=False)
class api20_bootstrap_base(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # run all OS install workflows first
        nodeindex = 0
        for item in OSLIST:
            # if OS proxy entry exists in RackHD config, run bootstrap against selected node
            if nodeindex < len(NODECATALOG):
                # delete active workflows for specified node
                fit_common.cancel_active_workflows(NODECATALOG[nodeindex])
                # base payload common to all Linux
                payload_data = {"options": {"defaults": {
                                "version": item['version'],
                                "repo": rackhdhost + item['path'],
                                "rootPassword": "1234567",
                                "hostname": "rackhdnode",
                                "users": [{"name": "rackhduser",
                                           "password": "RackHDRocks!",
                                           "uid": 1010}]}},
                                "reboot": "ipmi-obm-service",
                                "set-boot-pxe": "ipmi-obm-service"}

                # OS specific payload requirements
                if item['workflow'] == "Graph.InstallUbuntu":
                    payload_data["options"]["defaults"]["baseUrl"] = "install/netboot/ubuntu-installer/amd64"
                    payload_data["options"]["defaults"]["kargs"] = {"live-installer/net-image": rackhdhost +
                                                                    item['path'] +
                                                                    "/ubuntu/install/filesystem.squashfs"}
                # run workflow
                result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                              NODECATALOG[nodeindex] +
                                              '/workflows?name=' + item['workflow'],
                                              action='post', payload=payload_data)
                if result['status'] == 201:
                    # this saves the task and node IDs
                    NODE_STATUS[NODECATALOG[nodeindex]] = \
                        {"workflow": item['workflow'],
                         "version": item['version'],
                         "kvm": item['kvm'],
                         "id": result['json']['instanceId'],
                         "nodeID": NODECATALOG[nodeindex],
                         "StartTime": fit_common.time.time(),
                         "EndTime": 0}
                    log.info_5(" Workflow: %s  TaskID: %s", item['workflow'], result['json']['instanceId'])
                    log.info_5(" Payload: " + fit_common.json.dumps(payload_data))
                else:
                    # if no task ID is returned put 'failed' in ID field
                    NODE_STATUS[NODECATALOG[nodeindex]] = \
                        {"workflow": item['workflow'],
                         "version": item['version'],
                         "kvm": item['kvm'],
                         'id': "failed",
                         "wf_stime": "",
                         "wf_etime": ""}

                    log.error(" OS install %s on node %s failed!", item['workflow'], NODECATALOG[nodeindex])
                    log.error(" Error text: %s", result['text'])
                    log.error(" Payload: " + fit_common.json.dumps(payload_data))
                # increment node index to run next bootstrap
                nodeindex += 1

    def test01_api20_bootstrap_ubuntu14(self):
        taskid = node_taskid("Graph.InstallUbuntu", "trusty", False)
        wf_status = wait_for_workflow_complete(taskid)
        display_workflow_info(taskid)
        self.assertTrue(wf_status, "Ubuntu 14 failed.")

    def test02_api20_bootstrap_centos65(self):
        taskid = node_taskid("Graph.InstallCentOS", "6.5", False)
        wf_status = wait_for_workflow_complete(taskid)
        display_workflow_info(taskid)
        self.assertTrue(wf_status, "Centos 6.5 failed.")

    def test03_api20_bootstrap_esxi6(self):
        taskid = node_taskid("Graph.InstallESXi", "6.", False)
        wf_status = wait_for_workflow_complete(taskid)
        display_workflow_info(taskid)
        self.assertTrue(wf_status, "ESXi6.0 failed.")


if __name__ == '__main__':
    fit_common.unittest.main()
