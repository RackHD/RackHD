'''
Copyright 2015, EMC, Inc.

Author(s):
George Paulos

This script initializes OnRack stack.
'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common
import pdu_lib

# Locals
MAX_CYCLES = 60

class onrack_stack_init(fit_common.unittest.TestCase):
    def test01_preload_default_sku(self):
        # Load default SKU for unsupported compute nodes
        print '**** Installing default SKU'
        payload = {
                        "name": ["Unsupported-Compute"],
                        "rules": [
                            {
                                "path": "bmc.IP Address"
                            }
                        ]
                    }
        api_data = fit_common.rackhdapi("/api/1.1/skus", action='post', payload=payload)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expecting 200, got '
                         + str(api_data['status']))

    def test02_power_on_nodes(self):
        # ServerTech PDU case
        if pdu_lib.check_pdu_type() != "Unknown":
            print '**** PDU found, powering on PDU outlets'
            self.assertTrue(pdu_lib.pdu_control_compute_nodes("on"), 'Failed to power on all outlets')
            # Wait about 30 seconds for the outlets to all come on and nodes to DHCP
            fit_common.countdown(30)
        # no PDU case
        else:
            print '**** No supported PDU found, restarting nodes using IMPI.'
            # Power off all nodes
            self.assertNotEqual(fit_common.power_control_all_nodes("off"), 0, 'No BMC IP addresses found')
            # Power on all nodes
            self.assertNotEqual(fit_common.power_control_all_nodes("on"), 0, 'No BMC IP addresses found')

    # Optionally install control switch node if present
    @fit_common.unittest.skipUnless("control" in fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']], "")
    def test03_discover_control_switch_node(self):
        print "**** Creating control switch node."
        payload = {
                    "type":"switch",
                    "name":"Control",
                    "autoDiscover":True,
                    "snmpSettings":{
                        "host": fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']]['control'],
                        "community": fit_common.GLOBAL_CONFIG['snmp']['community'],
                    }
                    }
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got '
                         + str(api_data['status']))

    # Optionally install data switch node if present
    @fit_common.unittest.skipUnless("data" in fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']], "")
    def test04_discover_data_switch_node(self):
        print "**** Creating data switch node."
        payload = {
                    "type":"switch",
                    "name":"Data",
                    "autoDiscover":True,
                    "snmpSettings":{
                        "host": fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']]['data'],
                        "community": fit_common.GLOBAL_CONFIG['snmp']['community'],
                    }
                    }
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got '
                         + str(api_data['status']))

    # Optionally install PDU node if present
    @fit_common.unittest.skipUnless("pdu" in fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']], "")
    def test05_discover_pdu_node(self):
        print "**** Creating PDU node."
        payload = {
                    "type":"pdu",
                    "name":"PDU",
                    "autoDiscover":True,
                    "snmpSettings":{
                        "host": fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']]['pdu'],
                        "community": fit_common.GLOBAL_CONFIG['snmp']['community'],
                    }
                    }
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got '
                         + str(api_data['status']))

    def test06_check_compute_nodes(self):
        print "**** Waiting for compute nodes."
        c_index = 0
        for c_index in range(0, MAX_CYCLES):
            if "compute" in fit_common.rackhdapi("/api/2.0/nodes")['text']:
                break
            else:
                fit_common.time.sleep(30)
        self.assertLess(c_index, MAX_CYCLES-1, "No compute nodes settings found.")

    def test07_check_discovery(self):
        print "**** Waiting for node Discovery to complete.\n",
        # Determine if there are any active workflows. If returned value is true, obmSettings, SKUs
        # and active workflows are all either present or complete. If  the returned is false,
        # there was a timeout and all nodes have not obtained obmSetting, SKUs, or all active
        # workflows have not completed.
        # Wait 10 minutes ( MAX_CYCLES * 10 seconds) for this to occur.
        self.assertTrue(self.check_for_active_workflows(MAX_CYCLES), "Node discovery not completed")
        
    def check_for_active_workflows(self, max_time):
        '''
        Determine if are any active workflows.
        :param    Time to wait (in 10 second intervals)
        :return:  True  - No active workflows
                  False - Workflows are active
        '''
        for dummy in range(0, max_time):
            nodes_data = fit_common.rackhdapi("/api/2.0/nodes")
            if nodes_data['status'] == 200 and len(nodes_data['json']) > 0:
                # if there are nodes present, determine if discovery has completed on them
                discovery_complete = True

                for node in nodes_data['json']:
                    if node['type'] == 'compute':
                        self.assertIn('id', node, 'node does not contain id')
                        node_id = node['id']
                        # determine if there are any active worlflows. If so, discovery not completed
                        awf_data = fit_common.rackhdapi('/api/1.1/nodes/'
                                                           + node_id
                                                           + '/workflows/active')
                        # 204 indicates "No Content"
                        if awf_data['status'] != 204 or 'sku' not in node:
                            discovery_complete = False
                            break

                if discovery_complete:
                    return True
                fit_common.time.sleep(10)
        return False

    def test08_install_obm_credentials(self):
        print "**** Install OBM credentials."
        # install OBM credentials via workflows
        count = 0
        for creds in fit_common.GLOBAL_CONFIG['credentials']['bmc']:
            # greate graph for setting OBM credentials
            payload = \
            {
                "friendlyName": "IPMI" + str(count),
                "injectableName": 'Graph.Obm.Ipmi.CreateSettings' + str(count),
                "options": {
                    "obm-ipmi-task":{
                        "user": creds["username"],
                        "password": creds["password"]
                    }
                },
                "tasks": [
                    {
                        "label": "obm-ipmi-task",
                        "taskName": "Task.Obm.Ipmi.CreateSettings"
                    }
            ]
            }
            api_data = fit_common.rackhdapi("/api/1.1/workflows", action="put", payload=payload)
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expecting 200, got ' + str(api_data['status']))
            count += 1
        print "**** Configure node OBM settings."
        # run each OBM credential workflow on each node until success
        nodelist = fit_common.node_select()
        succeeded = True
        for node in nodelist:
            for num in range(0, count):
                status = ""
                workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings' + str(num)}
                # wait for existing workflow to complete
                for dummy in range(0, MAX_CYCLES):
                    result = fit_common.rackhdapi("/api/1.1/nodes/"  + node + "/workflows", action="post", payload=workflow)
                    if result['status'] != 201:
                        fit_common.time.sleep(5)
                    else:
                        break
                # wait for OBM workflow to complete
                counter = 0
                for counter in range(0, MAX_CYCLES):
                    fit_common.time.sleep(10)
                    status = fit_common.rackhdapi("/api/1.1/workflows/" + result['json']["instanceId"])['json']['_status']
                    if status != "running" and status != "pending":
                        break
                if status == "succeeded":
                    break
                if counter == MAX_CYCLES:
                    succeeded = False
                    print "*** Node failed OBM settings:", node
        self.assertTrue(succeeded, "OBM settings failed.")

    @fit_common.unittest.skipUnless("bmc" in fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']],"")
    @fit_common.unittest.skip("Skipping 'test09_add_management_server' due to ODR-803")
    def test09_add_management_server(self):
        print "**** Creating management server."
        usr = ""
        pwd = ""
        # find correct BMC passwords from global config
        for creds in fit_common.GLOBAL_CONFIG['credentials']['bmc']:
            if fit_common.remote_shell('ipmitool -I lanplus -H ' + fit_common.ARGS_LIST['bmc']
                                   + ' -U ' + creds['username'] + ' -P '
                                   + creds['password'] + ' fru')['exitcode'] == 0:
                usr = creds['username']
                pwd = creds['password']
        # create management node using these creds
        payload = {
                    "name":"Management Server",
                    "type": "compute",
                    "identifiers": fit_common.ARGS_LIST['bmc'],
                    "ipmi-obm-service": {
                        "host": fit_common.ARGS_LIST['bmc'],
                        "user": usr,
                        "password": pwd
                    }
                    }
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got '
                         + str(api_data['status']))
        # run discovery workflow
        payload = {
                    "name": "Graph.MgmtSKU.Discovery",
                    "options":{"defaults": {"nodeId": api_data['json']['id']}}
                    }
        api_data = fit_common.rackhdapi("/api/2.0/nodes/" + api_data['json']['id'] + "/workflows",
                                        action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got '
                         + str(api_data['status']))

    def test10_check_pollers(self):
        print "**** Waiting for pollers."
        # Determine if there are any poller present. If the return value is true, there are pollers
        # active. If the return value is false, pollers are not active.
        # Wait 10 minutes ( MAX_CYCLES * 10 seconds) for this to occur.
        self.assertTrue(self.check_for_active_pollers(MAX_CYCLES), 'No pollers')
        print "**** Waiting for pollers data."
        # Determine if all the pollers have data. If the return value is true, all pollers have data
        # If the return value is false, poller are working but not collecting data.
        # Wait 10 minutes ( MAX_CYCLES * 10 seconds) for this to occur.
        self.assertTrue(self.check_for_active_poller_data(MAX_CYCLES), 'All pollers are not active')

    def check_for_active_pollers(self, max_time):
        '''
        Determine if all poller are active.
        :param    Time to wait (in 10 second intervals)
        :return:  True  - Poller active
                  False - Pollers not active
        '''
        for dummy in range(0, max_time):
            api_data = fit_common.rackhdapi('/api/2.0/pollers')
            if len(api_data['json']) > 0:
                return True
            fit_common.time.sleep(30)
        return False

    def check_for_active_poller_data(self, max_time):
        '''
        Determine if all poller have data.
        :param    Time to wait (in 10 second intervals)
        :return:  True  - Poller have data
                  False - Not all poller have data
        '''
        api_data = fit_common.rackhdapi('/api/2.0/pollers')
        if api_data:
            for dummy in range(0, max_time):
                good_poller_data = True
                for index in  api_data['json']:

                    poll_data = fit_common.rackhdapi("/api/2.0/pollers/" + index['id'] + "/data")
                    if poll_data['status'] != 200 or len(poll_data['json']) == 0:
                        good_poller_data = False
                        break
                if good_poller_data:
                    return True
                fit_common.time.sleep(10)
        return False

    def test11_check_node_inventory(self):
        # this test will verify node inventory by BMC MAC if specified in STACK_CONFIG
        errorlist = []
        #check OBM MAC addresses
        if "nodes" in fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']]:
            nodecheck = fit_common.rackhdapi('/api/1.1/nodes')['text']
            for entry in fit_common.STACK_CONFIG[fit_common.ARGS_LIST['stack']]['nodes']:
                if entry['bmcmac'] not in str(nodecheck):
                    print '**** Missing node:' + entry['sku'] + "  BMC:" + entry['bmcmac']
                    errorlist.append(entry['bmcmac'])
            self.assertEqual(errorlist, [], "Missing nodes in catalog.")

if __name__ == '__main__':
    fit_common.unittest.main()