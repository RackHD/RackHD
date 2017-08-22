'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Author(s):
George Paulos

This script tests base case of the RackHD Redfish BootImage API and OS bootstrap workflows.
This routine runs OS bootstrap jobs simultaneously on multiple nodes.
For 8 tests to run, 8 nodes are required in the stack. If there are less than that, tests will be skipped.
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
statichost = "http://" + str(rackhdconfig['fileServerAddress']) + ":" + str(rackhdconfig['fileServerPort'])


# this routine polls a task ID for completion
def wait_for_task_complete(taskid, retries=60):
    for dummy in range(0, retries):
        result = fit_common.rackhdapi(taskid)
        if result['status'] != 200:
            log.error(" " + result['text'])
            return False
        if result['json']['TaskState'] == 'Running' or result['json']['TaskState'] == 'Pending':
            log.info_5("OS Install workflow state: {}".format(result['json']['TaskState']))
            fit_common.time.sleep(30)
        elif result['json']['TaskState'] == 'Completed':
            log.info_5("OS Install workflow state: {}".format(result['json']['TaskState']))
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
def node_taskid(osname, version):
    for entry in NODE_STATUS:
        if NODE_STATUS[entry]['os'] == osname and NODE_STATUS[entry]['version'] == version:
            return NODE_STATUS[entry]['id']
    return ""


OSLIST = [
    {"os": "ESXi", "version": "5.5", "path": "/ESXi/5.5", "kvm": False},
    {"os": "ESXi", "version": "6.0", "path": "/ESXi/6.0", "kvm": False},
    {"os": "CentOS", "version": "6.5", "path": "/CentOS/6.5", "kvm": False},
    {"os": "CentOS+KVM", "version": "6.5", "path": "/CentOS/6.5", "kvm": True},
    {"os": "CentOS", "version": "7", "path": "/CentOS/7.0", "kvm": False},
    {"os": "RHEL+KVM", "version": "7", "path": "/RHEL/7.0", "kvm": True},
    {"os": "RHEL", "version": "7", "path": "/RHEL/7.0", "kvm": False},
    {"os": "CentOS+KVM", "version": "7", "path": "/CentOS/7.0", "kvm": True}
]

# Match up tests to node IDs to feed skip decorators
index = 0  # node index
for item in OSLIST:
    if proxy_select(item['path']) and index < len(NODECATALOG):
        NODE_STATUS[NODECATALOG[index]] = {"os": item['os'], "version": item['version'], "id": "Pending"}
    index += 1

# ------------------------ Tests -------------------------------------


@attr(all=True, regression=True)
class redfish_bootstrap_base(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # run all OS install workflows first
        nodeindex = 0
        for item in OSLIST:
            # if OS proxy entry exists in RackHD config, run bootstrap against selected node
            if proxy_select(item['path']) and nodeindex < len(NODECATALOG):
                # delete active workflows for specified node
                fit_common.cancel_active_workflows(NODECATALOG[nodeindex])
                payload_data = {"osName": item['os'],
                                "version": item['version'],
                                "kvm": item['kvm'],
                                "repo": statichost + proxy_select(item['path']),
                                "rootPassword": "1234567",
                                "hostname": "rackhdnode",
                                "dnsServers": [rackhdconfig['apiServerAddress']],
                                "users": [{"name": "rackhd",
                                           "password": "R@ckHD1!",
                                           "uid": 1010}]}
                result = fit_common.rackhdapi('/redfish/v1/Systems/' +
                                              NODECATALOG[nodeindex] +
                                              '/Actions/RackHD.BootImage',
                                              action='post', payload=payload_data)
                if result['status'] == 202:
                    # this branch saves the task and node IDs
                    NODE_STATUS[NODECATALOG[nodeindex]] = \
                        {"os": item['os'], "version": item['version'], "id": result['json']['@odata.id']}
                    log.info_5(" TaskID: " + result['text'])
                    log.info_5(" Payload: " + fit_common.json.dumps(payload_data))
                else:
                    # this is the failure case where there is no task ID
                    NODE_STATUS[NODECATALOG[nodeindex]] = \
                        {"os": item['os'], "version": item['version'], 'id': "/redfish/v1/taskservice/tasks/failed"}
                    log.error(" TaskID: " + result['text'])
                    log.error(" Payload: " + fit_common.json.dumps(payload_data))
                # increment node index to run next bootstrap
                nodeindex += 1

    @fit_common.unittest.skipUnless(node_taskid("ESXi", "5.5") != '',
                                    "Skipping ESXi5.5, repo not configured or node unavailable")
    def test_redfish_bootstrap_esxi55(self):
        self.assertTrue(wait_for_task_complete(node_taskid("ESXi", "5.5")), "ESXi5.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("ESXi", "6.0") != '',
                                    "Skipping ESXi6.0, repo not configured or node unavailable")
    def test_redfish_bootstrap_esxi60(self):
        self.assertTrue(wait_for_task_complete(node_taskid("ESXi", "6.0")), "ESXi6.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS", "6.5") != '',
                                    "Skipping Centos 6.5, repo not configured or node unavailable")
    def test_redfish_bootstrap_centos65(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS", "6.5")), "Centos 6.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS+KVM", "6.5") != '',
                                    "Skipping Centos 6.5 KVM, repo not configured or node unavailable")
    def test_redfish_bootstrap_centos65_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS+KVM", "6.5")), "Centos 6.5 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS", "7") != '',
                                    "Skipping Centos 7.0, repo not configured or node unavailable")
    def test_redfish_bootstrap_centos70(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS", "7")), "Centos 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS+KVM", "7") != '',
                                    "Skipping Centos 7.0 KVM, repo not configured or node unavailable")
    def test_redfish_bootstrap_centos70_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS+KVM", "7")), "Centos 7.0 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("RHEL", "7") != '',
                                    "Skipping Redhat 7.0, repo not configured or node unavailable")
    def test_redfish_bootstrap_rhel70(self):
        self.assertTrue(wait_for_task_complete(node_taskid("RHEL", "7")), "RHEL 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("RHEL+KVM", "7") != '',
                                    "Skipping Redhat 7.0 KVM, repo not configured or node unavailable")
    def test_redfish_bootstrap_rhel70_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("RHEL+KVM", "7")), "RHEL 7.0 KVM failed.")


if __name__ == '__main__':
    fit_common.unittest.main()
