'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Author(s):
George Paulos

This script tests base case of the RackHD API 2.0 OS bootstrap workflows.
This routine runs OS bootstrap jobs simultaneously on multiple nodes.
For 11 tests to run, 11 nodes are required in the stack. If there are less than that, tests will be skipped.
This test takes 15-20 minutes to run.

OS bootstrap tests require special RackHD configuration and mirror repositories for the OS images.
OS images are loaded via RackHD "httpProxies" settings in config.json.

Example:
      "httpProxies": [
        {
          "localPath": "/ESXi/5.5",
          "remotePath": "/",
          "server": "http://os-mirror-server/esxi/5.5/esxi"
        },
        {
          "localPath": "/ESXi/6.0",
          "remotePath": "/",
          "server": "http://os-mirror-server/6.0/esxi6"
        },
        {
          "localPath": "/CentOS/6.5",
          "remotePath": "/",
          "server": "http://os-mirror-server/centos/6.5/os/x86_64"
        },
        {
          "localPath": "/CentOS/7.0",
          "remotePath": "/",
          "server": "http://os-mirror-server/centos/7/os/x86_64"
        },
        {
          "localPath": "/RHEL/7.0",
          "remotePath": "/",
          "server": "http://os-mirror-server/rhel/7.0/os/x86_64"
        },
        {
          "localPath": "/coreos",
          "remotePath": "/",
          "server": "http://os-mirror-server/mirrors/coreos/17"
        },
        {
          "localPath": "/SLES/12",
          "remotePath": "/",
          "server": "http://os-mirror-server/mirrors/sles/12"
        },
        {
          "localPath": "/Ubuntu/14",
          "remotePath": "/",
          "server": "http://os-mirror-server/mirrors/ubuntu/boot/14.04.4"
        }
      ],

For each OS type, the "localpath" string must conform to the convention above.
The "server' URL points to the location of the OS executables in an image repository.

'''

import fit_path  # NOQA: unused import
from nose.plugins.attrib import attr
import fit_common
import flogging
log = flogging.get_loggers()

# This gets the list of nodes
NODECATALOG = fit_common.node_select()

# dict containing bootstrap workflow IDs and states
NODE_STATUS = {}

# download RackHD config from host
rackhdconfig = fit_common.rackhdapi('/api/2.0/config')['json']
rackhdhost = "http://" + str(rackhdconfig['apiServerAddress']) + ":" + str(rackhdconfig['apiServerPort'])


# this routine polls a task ID for completion
def wait_for_task_complete(taskid, retries=60):
    for dummy in range(0, retries):
        result = fit_common.rackhdapi("/api/2.0/workflows/" + taskid)
        if result['status'] != 200:
            log.error(" " + result['text'])
            return False
        if result['json']['status'] == 'running' or result['json']['status'] == 'pending':
            log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            fit_common.time.sleep(30)
        elif result['json']['status'] == 'succeeded':
            log.info_5("{} workflow status: {}".format(result['json']['injectableName'], result['json']['status']))
            log.info_5(" " + result['text'])
            return True
        else:
            log.error(" " + result['text'])
            return False
    log.error(" Workflow Timeout: " + result['text'])
    return False


# helper routine for selecting OS image path by matching proxy 'localPath'
def proxy_select(tag):
    for entry in rackhdconfig['httpProxies']:
        if tag == entry['localPath']:
            return entry['localPath']
    return ''


# helper routine to return the task ID associated with the running bootstrap workflow
def node_taskid(workflow, version, kvm):
    for entry in NODE_STATUS:
        if NODE_STATUS[entry]['workflow'] == workflow \
                and NODE_STATUS[entry]['version'] == version \
                and NODE_STATUS[entry]['kvm'] == kvm:
            return NODE_STATUS[entry]['id']
    return ""


OSLIST = [
    {"workflow": "Graph.InstallESXi", "version": "5.5", "path": "/ESXi/5.5", "kvm": False},
    {"workflow": "Graph.InstallESXi", "version": "6.0", "path": "/ESXi/6.0", "kvm": False},
    {"workflow": "Graph.InstallCentOS", "version": "6.5", "path": "/CentOS/6.5", "kvm": False},
    {"workflow": "Graph.InstallCentOS", "version": "7", "path": "/CentOS/7.0", "kvm": False},
    {"workflow": "Graph.InstallRHEL", "version": "7", "path": "/RHEL/7.0", "kvm": False},
    {"workflow": "Graph.InstallSUSE", "version": "12", "path": "/SLES/12", "kvm": False},
    {"workflow": "Graph.InstallUbuntu", "version": "trusty", "path": "/Ubuntu/14", "kvm": False},
    {"workflow": "Graph.InstallCoreOS", "version": "899.17.0", "path": "/coreos", "kvm": False},
    {"workflow": "Graph.InstallRHEL", "version": "7", "path": "/RHEL/7.0", "kvm": True},
    {"workflow": "Graph.InstallCentOS", "version": "6.5", "path": "/CentOS/6.5", "kvm": True},
    {"workflow": "Graph.InstallCentOS", "version": "7", "path": "/CentOS/7.0", "kvm": True}
]

# Match up tests to node IDs to feed skip decorators
index = 0  # node index
for item in OSLIST:
    if proxy_select(item['path']) and index < len(NODECATALOG):
        NODE_STATUS[NODECATALOG[index]] = \
            {"workflow": item['workflow'], "version": item['version'], "kvm": item['kvm'], "id": "Pending"}
    index += 1

# ------------------------ Tests -------------------------------------


@attr(all=True, regression=True)
class api20_bootstrap_base(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # run all OS install workflows first
        nodeindex = 0
        for item in OSLIST:
            # if OS proxy entry exists in RackHD config, run bootstrap against selected node
            if proxy_select(item['path']) and nodeindex < len(NODECATALOG):
                # delete active workflows for specified node
                fit_common.cancel_active_workflows(NODECATALOG[nodeindex])
                payload_data = {"options": {"defaults": {
                                "version": item['version'],
                                "kvm": item['kvm'],
                                "repo": rackhdhost + proxy_select(item['path']),
                                "rootPassword": "1234567",
                                "hostname": "rackhdnode",
                                "dnsServers": [rackhdconfig['apiServerAddress']],
                                "users": [{"name": "rackhduser",
                                           "password": "RackHDRocks!",
                                           "uid": 1010}]}}}
                # OS specific requirements
                if item['workflow'] == "Graph.InstallUbuntu":
                    payload_data["options"]["defaults"]["baseUrl"] = "install/netboot/ubuntu-installer/amd64"
                    payload_data["options"]["defaults"]["kargs"] = {"live-installer/net-image": rackhdhost + proxy_select(item['path']) + "/ubuntu/install/filesystem.squashfs"}
                # run workflow
                result = fit_common.rackhdapi('/api/2.0/nodes/' +
                                              NODECATALOG[nodeindex] +
                                              '/workflows?name=' + item['workflow'],
                                              action='post', payload=payload_data)
                if result['status'] == 201:
                    # this branch saves the task and node IDs
                    NODE_STATUS[NODECATALOG[nodeindex]] = \
                        {"workflow": item['workflow'],
                         "version": item['version'],
                         "kvm": item['kvm'],
                         "id": result['json']['instanceId']}
                    log.info_5(" TaskID: " + result['text'])
                    log.info_5(" Payload: " + fit_common.json.dumps(payload_data))
                else:
                    # this is the failure case where there is no task ID
                    NODE_STATUS[NODECATALOG[nodeindex]] = \
                        {"workflow": item['workflow'],
                         "version": item['version'],
                         "kvm": item['kvm'],
                         'id': "failed"}
                    log.error(" TaskID: " + result['text'])
                    log.error(" Payload: " + fit_common.json.dumps(payload_data))
                # increment node index to run next bootstrap
                nodeindex += 1

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallESXi", "5.5", False) != '',
                                    "Skipping ESXi5.5, repo not configured or node unavailable")
    def test_api20_bootstrap_esxi55(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallESXi", "5.5", False)), "ESXi5.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallESXi", "6.0", False) != '',
                                    "Skipping ESXi6.0, repo not configured or node unavailable")
    def test_api20_bootstrap_esxi60(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallESXi", "6.0", False)), "ESXi6.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "6.5", False) != '',
                                    "Skipping Centos 6.5, repo not configured or node unavailable")
    def test_api20_bootstrap_centos65(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallCentOS", "6.5", False)), "Centos 6.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "6.5", True) != '',
                                    "Skipping Centos 6.5 KVM, repo not configured or node unavailable")
    def test_api20_bootstrap_centos65_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallCentOS", "6.5", True)), "Centos 6.5 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "7", False) != '',
                                    "Skipping Centos 7.0, repo not configured or node unavailable")
    def test_api20_bootstrap_centos70(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallCentOS", "7", False)), "Centos 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCentOS", "7", True) != '',
                                    "Skipping Centos 7.0 KVM, repo not configured or node unavailable")
    def test_api20_bootstrap_centos70_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallCentOS", "7", True)), "Centos 7.0 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallRHEL", "7", False) != '',
                                    "Skipping Redhat 7.0, repo not configured or node unavailable")
    def test_api20_bootstrap_rhel70(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallRHEL", "7", False)), "RHEL 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallRHEL", "7", True) != '',
                                    "Skipping Redhat 7.0 KVM, repo not configured or node unavailable")
    def test_api20_bootstrap_rhel70_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallRHEL", "7", True)), "RHEL 7.0 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallUbuntu", "trusty", False) != '',
                                    "Skipping Ubuntu 14, repo not configured or node unavailable")
    def test_api20_bootstrap_ubuntu14(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallUbuntu", "trusty", False)), "Ubuntu 14 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallCoreOS", "899.17.0", False) != '',
                                    "Skipping CoreOS 899.17.0, repo not configured or node unavailable")
    def test_api20_bootstrap_coreos899_17(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallCoreOS", "899.17.0", False)), "CoreOS 899.17 failed.")

    @fit_common.unittest.skipUnless(node_taskid("Graph.InstallSUSE", "12", False) != '',
                                    "Skipping SuSe 12, repo not configured or node unavailable")
    def test_api20_bootstrap_suse12(self):
        self.assertTrue(wait_for_task_complete(node_taskid("Graph.InstallSUSE", "12", False)), "SuSe 12 failed.")


if __name__ == '__main__':
    fit_common.unittest.main()
