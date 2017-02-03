# Copyright 2017, EMC, Inc.

'''
This script tests base case of the RackHD Redfish BootImage API and OS bootstrap workflows
The test will select a single eligible node to run all currently supported bootstrap workflows
This is a LONG-RUNNING script which will typically take 1-2 hours to execute

Bootstrap tests require special RackHD configuration and mirror repositories for the OS images
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

For each OS type, the "localpath" string must conform to the schema above.
The "server' URL points to the location of the OS executables in an image repository.

'''

import os
import sys
import subprocess
import random

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# This node catalog section will be replaced with fit_common.node_select() when it is checked in
NODECATALOG = fit_common.node_select()

NODE = ""
# Select one node at random
NODE = NODECATALOG[random.randint(0, len(NODECATALOG)-1)]

# this routine polls a task ID for completion
def wait_for_task_complete(taskid, retries=60):
    for dummy in range(0, retries):
        result = fit_common.rackhdapi(taskid)
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

# download RackHD config from host
rackhdconfig = fit_common.rackhdapi('/api/2.0/config')['json']
httpProxies = rackhdconfig['httpProxies']
rackhdhost = "http://" + str(rackhdconfig['apiServerAddress']) + ":" + str(rackhdconfig['apiServerPort'])

# helper routine for selecting OS image path by matching proxy path
def proxySelect(tag):
    for entry in httpProxies:
        if tag in entry['localPath']:
            return entry['localPath']
    return ''

# ------------------------ Tests -------------------------------------
from nose.plugins.attrib import attr
@attr(all=True)
class os_bootstrap_base(fit_common.unittest.TestCase):
    def setUp(self):
        #delete active workflows for specified node
        fit_common.cancel_active_workflows(NODE)

    @fit_common.unittest.skipUnless(proxySelect('ESXi/5.5') != '', "Skipping ESXi5.5, repo not configured")
    def test_bootstrap_esxi55(self):
        if fit_common.VERBOSITY >= 2:
            print 'Running ESXI 5.5 bootstrap.'
        nodehostname = 'esxi55'
        payload_data = {
                        "osName": "ESXi",
                        "version": "5.5",
                        "repo": rackhdhost + proxySelect('ESXi/5.5'),
                        "rootPassword": "1234567",
                        "hostname": nodehostname,
                        "domain": "rackhd.local",
                        "dnsServers": [rackhdconfig['apiServerAddress']],
                        "users": [{
                                    "name": "onrack",
                                    "password": "Onr@ck1!",
                                    "uid": 1010,
                                }]
                       }
        result = fit_common.rackhdapi('/redfish/v1/Systems/'
                                            + NODE
                                            + '/Actions/RackHD.BootImage',
                                            action='post', payload=payload_data)
        self.assertEqual(result['status'], 202,
                         'Was expecting code 202. Got ' + str(result['status']))
        self.assertEqual(wait_for_task_complete(result['json']['@odata.id'], retries=80), True,
                         'TaskID ' + result['json']['@odata.id'] + ' not successfully completed.')


    @fit_common.unittest.skipUnless(proxySelect('ESXi/6.0') != '', "Skipping ESXi6.0, repo not configured")
    def test_bootstrap_esxi60(self):
        if fit_common.VERBOSITY >= 2:
            print 'Running ESXI 6.0 bootstrap.'
        nodehostname = 'esxi60'
        payload_data = {"osName": "ESXi",
                        "version": "6.0",
                        "repo": rackhdhost + proxySelect('ESXi/6.0'),
                        "rootPassword": "1234567",
                        "hostname": nodehostname,
                        "domain": "rackhd.local",
                        "dnsServers": [rackhdconfig['apiServerAddress']],
                        "users": [{
                                    "name": "onrack",
                                    "password": "Onr@ck1!",
                                    "uid": 1010,
                                }]
                       }
        result = fit_common.rackhdapi('/redfish/v1/Systems/'
                                            + NODE
                                            + '/Actions/RackHD.BootImage',
                                            action='post', payload=payload_data)
        self.assertEqual(result['status'], 202,
                         'Was expecting code 202. Got ' + str(result['status']))
        self.assertEqual(wait_for_task_complete(result['json']['@odata.id'], retries=80), True,
                         'TaskID ' + result['json']['@odata.id'] + ' not successfully completed.')


    @fit_common.unittest.skipUnless(proxySelect('CentOS/6.5') != '', "Skipping Centos 6.5, repo not configured")
    def test_bootstrap_centos65(self):
        if fit_common.VERBOSITY >= 2:
            print 'Running CentOS 6.5 bootstrap.'
        nodehostname = 'centos65'
        payload_data = {"osName": "CentOS",
                        "version": "6.5",
                        "repo": rackhdhost + proxySelect('CentOS/6.5'),
                        "rootPassword": "1234567",
                        "hostname": nodehostname,
                        "domain": "rackhd.local",
                        "dnsServers": [rackhdconfig['apiServerAddress']],
                        "users": [{
                                    "name": "onrack",
                                    "password": "onrack",
                                    "uid": 1010,
                                }]
                       }
        result = fit_common.rackhdapi('/redfish/v1/Systems/'
                                            + NODE
                                            + '/Actions/RackHD.BootImage',
                                            action='post', payload=payload_data)
        self.assertEqual(result['status'], 202,
                         'Was expecting code 202. Got ' + str(result['status']))
        self.assertEqual(wait_for_task_complete(result['json']['@odata.id']), True,
                         'TaskID ' + result['json']['@odata.id'] + ' not successfully completed.')


    @fit_common.unittest.skipUnless(proxySelect('CentOS/7.0') != '', "Skipping Centos 7.0, repo not configured")
    def test_bootstrap_centos70(self):
        if fit_common.VERBOSITY >= 2:
            print 'Running CentOS 7 bootstrap...'
        nodehostname = 'centos70'
        payload_data = {"osName": "CentOS",
                        "version": "7",
                        "repo": rackhdhost + proxySelect('CentOS/7.0'),
                        "rootPassword": "1234567",
                        "hostname": nodehostname,
                        "domain": "rackhd.local",
                        "dnsServers": [rackhdconfig['apiServerAddress']],
                        "users": [{
                                    "name": "onrack",
                                    "password": "onrack",
                                    "uid": 1010,
                                }],

                       }
        result = fit_common.rackhdapi('/redfish/v1/Systems/'
                                            + NODE
                                            + '/Actions/RackHD.BootImage',
                                            action='post', payload=payload_data)
        self.assertEqual(result['status'], 202,
                         'Was expecting code 202. Got ' + str(result['status']))
        self.assertEqual(wait_for_task_complete(result['json']['@odata.id']), True,
                         'TaskID ' + result['json']['@odata.id'] + ' not successfully completed.')


    @fit_common.unittest.skipUnless(proxySelect('CentOS/6.5') != '', "Skipping Centos 6.5 KVM, repo not configured")
    def test_bootstrap_centos65_kvm(self):
        if fit_common.VERBOSITY >= 2:
            print 'Running CentOS 6.5 KVM bootstrap.'
        nodehostname = 'centos65'
        payload_data = {"osName": "CentOS+KVM",
                        "version": "6.5",
                        "repo": rackhdhost + proxySelect('CentOS/6.5'),
                        "rootPassword": "1234567",
                        "hostname": nodehostname,
                        "domain": "rackhd.local",
                        "dnsServers": [rackhdconfig['apiServerAddress']],
                        "users": [{
                                    "name": "onrack",
                                    "password": "onrack",
                                    "uid": 1010,
                                }]
                       }
        result = fit_common.rackhdapi('/redfish/v1/Systems/'
                                            + NODE
                                            + '/Actions/RackHD.BootImage',
                                            action='post', payload=payload_data)
        self.assertEqual(result['status'], 202,
                         'Was expecting code 202. Got ' + str(result['status']))
        self.assertEqual(wait_for_task_complete(result['json']['@odata.id']), True,
                         'TaskID ' + result['json']['@odata.id'] + ' not successfully completed.')


    @fit_common.unittest.skipUnless(proxySelect('RHEL/7.0') != '', "Skipping Redhat 7.0, repo not configured")
    def test_bootstrap_rhel70_kvm(self):
        if fit_common.VERBOSITY >= 2:
            print 'Running RHEL 7 KVM bootstrap.'
        nodehostname = 'rhel70'
        payload_data = {"osName": "RHEL+KVM",
                        "version": "7",
                        "repo": rackhdhost + proxySelect('RHEL/7.0'),
                        "rootPassword": "1234567",
                        "hostname": nodehostname,
                        "domain": "rackhd.local",
                        "dnsServers": [rackhdconfig['apiServerAddress']],
                        "users": [{
                                    "name": "onrack",
                                    "password": "onrack",
                                    "uid": 1010,
                                }],

                       }
        result = fit_common.rackhdapi('/redfish/v1/Systems/'
                                            + NODE
                                            + '/Actions/RackHD.BootImage',
                                            action='post', payload=payload_data)
        self.assertEqual(result['status'], 202,
                         'Was expecting code 202. Got ' + str(result['status']))
        self.assertEqual(wait_for_task_complete(result['json']['@odata.id']), True,
                         'TaskID ' + result['json']['@odata.id'] + ' not successfully completed.')

if __name__ == '__main__':
    fit_common.unittest.main()
