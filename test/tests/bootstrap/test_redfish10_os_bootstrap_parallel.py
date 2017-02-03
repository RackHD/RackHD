'''
Copyright 2017, EMC, Inc.

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

import os
import sys
import subprocess

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# This gets the list of nodes
NODECATALOG = fit_common.node_select()

# download RackHD config from host
rackhdconfig = fit_common.rackhdapi('/api/2.0/config')['json']
httpProxies = rackhdconfig['httpProxies']
rackhdhost = "http://" + str(rackhdconfig['apiServerAddress']) + ":" + str(rackhdconfig['apiServerPort'])

# dict containing bootstrap workflow IDs and states
status = {}

# this routine polls a task ID for completion
def wait_for_task_complete(taskid, retries=60):
    for dummy in range(0, retries):
        result = fit_common.rackhdapi(taskid)
        if result['status'] != 200:
            return False
        if result['json']['TaskState'] == 'Running' or result['json']['TaskState'] == 'Pending':
            if fit_common.VERBOSITY >= 2:
                print "OS Install workflow state: {}".format(result['json']['TaskState'])
            fit_common.time.sleep(30)
        elif result['json']['TaskState'] == 'Completed':
            if fit_common.VERBOSITY >= 2:
                print "OS Install workflow state: {}".format(result['json']['TaskState'])
            return True
        else:
            break
    print "Task failed with the following state: " + result['json']['TaskState']
    return False

# helper routine for selecting OS image path by matching proxy path
def proxySelect(tag):
    for entry in httpProxies:
        if tag in entry['localPath']:
            return entry['localPath']
    return ''

# run individual bootstrap with parameters
def run_bootstrap_instance(node, osname, version, path):
    #delete active workflows for specified node
    fit_common.cancel_active_workflows(node)
    payload_data = {
                    "osName": osname,
                    "version": version,
                    "repo": rackhdhost + path,
                    "rootPassword": "1234567",
                    "hostname": "rackhdnode",
                    "dnsServers": [rackhdconfig['apiServerAddress']],
                    "users": [{
                                "name": "rackhd",
                                "password": "R@ckHD1!",
                                "uid": 1010,
                            }]
                   }
    result = fit_common.rackhdapi('/redfish/v1/Systems/'
                                        + node
                                        + '/Actions/RackHD.BootImage',
                                        action='post', payload=payload_data)
    if result['status'] == 202:
        status[node] = {"os":osname, "version":version, "id":result['json']['@odata.id']}
    else:
        status[node] = {"os":osname, "version":version, 'id':"/redfish/v1/taskservice/tasks/failed"}

# run all bootstraps on available nodes
def launch_bootstraps():
    oslist = [
        {"os":"ESXi", "version":"5.5", "path":"/ESXi/5.5"},
        {"os":"ESXi", "version":"6.0", "path":"/ESXi/6.0"},
        {"os":"CentOS", "version":"6.5", "path":"/CentOS/6.5"},
        {"os":"CentOS+KVM", "version":"6.5", "path":"/CentOS/6.5"},
        {"os":"CentOS", "version":"7", "path":"/CentOS/7.0"},
        {"os":"RHEL+KVM", "version":"7", "path":"/CentOS/7.0"},
        {"os":"RHEL", "version":"7", "path":"/RHEL/7.0"},
        {"os":"CentOS+KVM", "version":"7", "path":"/RHEL/7.0"}
    ]
    nodeindex = 0
    for item in oslist:
        # if OS proxy entry exists, run bootstrap against selected node
        if proxySelect(item['path']) and nodeindex < len(NODECATALOG):
            run_bootstrap_instance(NODECATALOG[nodeindex],item['os'],item['version'],item['path'])
            nodeindex += 1

# return the task ID associated with the running bootstrap workflow
def node_taskid(osname, version):
    for entry in status:
        if status[entry]['os'] == osname and status[entry]['version'] == version:
            return status[entry]['id']
    return ""

launch_bootstraps()

# ------------------------ Tests -------------------------------------
from nose.plugins.attrib import attr
@attr(all=True, regression=True)
class os_bootstrap_base(fit_common.unittest.TestCase):

    @fit_common.unittest.skipUnless(node_taskid("ESXi", "5.5") != '', "Skipping ESXi5.5")
    def test_bootstrap_esxi55(self):
        self.assertTrue(wait_for_task_complete(node_taskid("ESXi", "5.5")), "ESXi5.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("ESXi", "6.0")  != '', "Skipping ESXi6.0")
    def test_bootstrap_esxi60(self):
        self.assertTrue(wait_for_task_complete(node_taskid("ESXi", "6.0")), "ESXi6.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS", "6.5")  != '', "Skipping Centos 6.5")
    def test_bootstrap_centos65(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS", "6.5")), "Centos 6.5 failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS+KVM", "6.5") != '', "Skipping Centos 6.5 KVM")
    def test_bootstrap_centos65_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS+KVM", "6.5")), "Centos 6.5 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS", "7") != '', "Skipping Centos 7.0")
    def test_bootstrap_centos70(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS", "7")), "Centos 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("CentOS+KVM", "7") != '', "Skipping Centos 7.0 KVM")
    def test_bootstrap_centos70_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("CentOS+KVM", "7")), "Centos 7.0 KVM failed.")

    @fit_common.unittest.skipUnless(node_taskid("RHEL", "7") != '', "Skipping Redhat 7.0")
    def test_bootstrap_rhel70(self):
        self.assertTrue(wait_for_task_complete(node_taskid("RHEL", "7")), "RHEL 7.0 failed.")

    @fit_common.unittest.skipUnless(node_taskid("RHEL+KVM", "7") != '', "Skipping Redhat 7.0 KVM")
    def test_bootstrap_rhel70_kvm(self):
        self.assertTrue(wait_for_task_complete(node_taskid("RHEL+KVM", "7")), "RHEL 7.0 KVM failed.")

if __name__ == '__main__':
    fit_common.unittest.main()
