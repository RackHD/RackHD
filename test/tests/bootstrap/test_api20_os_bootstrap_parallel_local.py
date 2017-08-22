'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Author(s):
George Paulos

This script tests minimum payload base case of the RackHD API 2.0 OS bootstrap workflows using NFS mount or local repo method.
This routine runs OS bootstrap jobs simultaneously on multiple nodes.
For 12 tests to run, 12 nodes are required in the stack. If there are less than that, tests will be skipped.
This test takes 15-20 minutes to run.

OS bootstrap tests require the following entries in config/install_default.json.
If an entry is missing, then that test will be skipped.
The order of entries determines the priority of the test. First one runs on first available node, etc.

        "os-install": [
            {
                "kvm": false,
                "path": "/repo/esxi/5.5",
                "version": "5.5",
                "workflow": "Graph.InstallESXi"
            },
            {
                "kvm": false,
                "path": "/repo/esxi/6.0",
                "version": "6.0",
                "workflow": "Graph.InstallESXi"
            },
            {
                "kvm": false,
                "path": "/repo/centos/6.5",
                "version": "6.5",
                "workflow": "Graph.InstallCentOS"
            },
            {
                "kvm": false,
                "path": "/repo/centos/7.0",
                "version": "7.0",
                "workflow": "Graph.InstallCentOS"
            },
            {
                "kvm": false,
                "path": "/repo/rhel/7.0",
                "version": "7.0",
                "workflow": "Graph.InstallRHEL"
            },
            {
                "kvm": false,
                "path": "/repo/suse/42.1",
                "version": "42.1",
                "workflow": "Graph.InstallSUSE"
            },
            {
                "kvm": false,
                "path": "/repo/ubuntu",
                "version": "trusty",
                "workflow": "Graph.InstallUbuntu"
            },
            {
                "kvm": false,
                "path": "/repo/coreos",
                "version": "899.17.0",
                "workflow": "Graph.InstallCoreOS"
            },
            {
                "kvm": true,
                "path": "/repo/rhel/7.0",
                "version": "7.0",
                "workflow": "Graph.InstallRHEL"
            },
            {
                "kvm": true,
                "path": "/repo/centos/6.5",
                "version": "6.5",
                "workflow": "Graph.InstallCentOS"
            },
            {
                "kvm": false,
                "path": "/repo/winpe",
                "productkey": "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX",
                "smbPassword": "onrack",
                "smbRepo": "\\windowsServer2012",
                "smbUser": "onrack",
                "version": "2012",
                "workflow": "Graph.InstallWindowsServer"
            }
        ],

The OS repos are to be installed under 'on-http/static/http' directory reflecting the paths above.
These can be files, links, or nfs mounts to remote repos in the following dirs:

on-http/static/http/windowsServer2012 -- requires Samba share on RackHD server
on-http/static/http/repo/centos/6.5
on-http/static/http/repo/centos/7.0
on-http/static/http/repo/rhel/7.0
on-http/static/http/repo/suse/42.1
on-http/static/http/repo/esxi/5.5
on-http/static/http/repo/esxi/6.0
on-http/static/http/repo/winpe
on-http/static/http/repo/coreos/899.17.0

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

# collect repo information from config files
OSLIST = fit_common.fitcfg()["install-config"]["os-install"]

# download RackHD config from host
rackhdresult = fit_common.rackhdapi('/api/2.0/config')
if rackhdresult['status'] != 200:
    log.error(" Unable to contact host, exiting. ")
    sys.exit(255)
rackhdconfig = rackhdresult['json']
statichost = "http://" + str(rackhdconfig['fileServerAddress']) + ":" + str(rackhdconfig['fileServerPort'])



# this routine polls a workflow task ID for completion
def wait_for_workflow_complete(taskid):
    result = None
    while fit_common.time.time() - START_TIME < 1800 or result is None:  # limit test to 30 minutes
        result = fit_common.rackhdapi("/api/2.0/workflows/" + taskid)
        if result['status'] != 200:
            log.error(" HTTP error: " + result['text'])
            return False
        if result['json']['status'] == 'running' or result['json']['status'] == 'pending':
            log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            fit_common.time.sleep(30)
        elif result['json']['status'] == 'succeeded':
            log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            return True
        else:
            log.error(" Workflow failed: " + result['text'])
            return False
    log.error(" Workflow Timeout: " + result['text'])
    return False


# helper routine to return the task ID associated with the running bootstrap workflow
def node_taskid(workflow, version, kvm):
    for entry in NODE_STATUS:
        if NODE_STATUS[entry]['workflow'] == workflow \
                and str(version) in NODE_STATUS[entry]['version'] \
                and NODE_STATUS[entry]['kvm'] == kvm:
            return NODE_STATUS[entry]['id']
    return ""


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
                                "kvm": item['kvm'],
                                "repo": statichost + item['path'],
                                "rootPassword": "1234567",
                                "hostname": "rackhdnode",
                                "users": [{"name": "rackhduser",
                                           "password": "RackHDRocks!",
                                           "uid": 1010}]}}}
                # OS specific payload requirements
                if item['workflow'] == "Graph.InstallUbuntu":
                    payload_data["options"]["defaults"]["baseUrl"] = "install/netboot/ubuntu-installer/amd64"
                    payload_data["options"]["defaults"]["kargs"] = {"live-installer/net-image": statichost +
                                                                    item['path'] + "/ubuntu/install/filesystem.squashfs"}
                if item['workflow'] == "Graph.InstallWindowsServer":
                    payload_data["options"]["defaults"]["productkey"] = item['productkey']
                    payload_data["options"]["defaults"]["smbUser"] = item['smbUser']
                    payload_data["options"]["defaults"]["smbPassword"] = item['smbPassword']
                    payload_data["options"]["defaults"]["smbRepo"] = "\\\\" + str(rackhdconfig['apiServerAddress']) + \
                                                                     item['smbRepo']
                    payload_data["options"]["defaults"]["username"] = "rackhduser"
                    payload_data["options"]["defaults"]["password"] = "RackHDRocks!"
                    payload_data["options"]["defaults"].pop('rootPassword', None)
                    payload_data["options"]["defaults"].pop('users', None)
                    payload_data["options"]["defaults"].pop('kvm', None)
                    payload_data["options"]["defaults"].pop('version', None)

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
                         "id": result['json']['instanceId']}
                    log.info_5(" TaskID: " + result['json']['instanceId'])
                    log.info_5(" Payload: " + fit_common.json.dumps(payload_data))
                else:
                    # if no task ID is returned put 'failed' in ID field
                    NODE_STATUS[NODECATALOG[nodeindex]] = \
                        {"workflow": item['workflow'],
                         "version": item['version'],
                         "kvm": item['kvm'],
                         'id': "failed"}
                    log.error(" OS install " + item['workflow'] + " on node " + NODECATALOG[nodeindex] + " failed! ")
                    log.error(" Error text: " + result['text'])
                    log.error(" Payload: " + fit_common.json.dumps(payload_data))
                # increment node index to run next bootstrap
                nodeindex += 1

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallESXi", "5.", False) != '',
                                    "Skipping ESXi5.5, repo not configured or node unavailable")
    def test_api20_bootstrap_esxi5(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallESXi", "5.", False)), "ESXi5.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallESXi", "6.", False) != '',
                                    "Skipping ESXi6.0, repo not configured or node unavailable")
    def test_api20_bootstrap_esxi6(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallESXi", "6.", False)), "ESXi6.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "6.", False) != '',
                                    "Skipping Centos 6.5, repo not configured or node unavailable")
    def test_api20_bootstrap_centos6(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallCentOS", "6.", False)), "Centos 6.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "6.", True) != '',
                                    "Skipping Centos 6.5 KVM, repo not configured or node unavailable")
    def test_api20_bootstrap_centos6_kvm(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallCentOS", "6.", True)), "Centos 6.5 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "7.", False) != '',
                                    "Skipping Centos 7.0, repo not configured or node unavailable")
    def test_api20_bootstrap_centos7(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallCentOS", "7.", False)), "Centos 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "7.", True) != '',
                                    "Skipping Centos 7.0 KVM, repo not configured or node unavailable")
    def test_api20_bootstrap_centos7_kvm(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallCentOS", "7.", True)), "Centos 7.0 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallRHEL", "7.", False) != '',
                                    "Skipping Redhat 7.0, repo not configured or node unavailable")
    def test_api20_bootstrap_rhel7(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallRHEL", "7.", False)), "RHEL 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallRHEL", "7.", True) != '',
                                    "Skipping Redhat 7.0 KVM, repo not configured or node unavailable")
    def test_api20_bootstrap_rhel7_kvm(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallRHEL", "7.", True)), "RHEL 7.0 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallUbuntu", "trusty", False) != '',
                                    "Skipping Ubuntu 14, repo not configured or node unavailable")
    def test_api20_bootstrap_ubuntu14(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallUbuntu", "trusty", False)), "Ubuntu 14 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCoreOS", "899.", False) != '',
                                    "Skipping CoreOS 899.17.0, repo not configured or node unavailable")
    def test_api20_bootstrap_coreos899(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallCoreOS", "899.", False)), "CoreOS 899.17 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallSUSE", "42.", False) != '',
                                    "Skipping SuSe 42, repo not configured or node unavailable")
    def test_api20_bootstrap_suse(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallSUSE", "42.", False)), "SuSe 42 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallWindowsServer", "2012", False) != '',
                                    "Skipping Windows 2012, repo not configured or node unavailable")
    def test_api20_bootstrap_windows(self):
        self.assertTrue(wait_for_workflow_complete(node_taskid("Graph.InstallWindowsServer", "2012", False)), "Win2012 failed.")


if __name__ == '__main__':
    fit_common.unittest.main()
