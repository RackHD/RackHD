'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

This script initializes RackHD stack after install.
    - loads SKU packs
    - loads default SKU
    - sets auth user
    - restarts nodes for discovery
    - discovers switches and/or PDUs if available
    - checks node discovery
    - assigns node OBM settings
    - checks pollers for data

'''

import fit_path  # NOQA: unused import
import os
import subprocess
import json
import time
import unittest
import fit_common
import pdu_lib
import flogging
import test_api_utils

log = flogging.get_loggers()

# Locals
MAX_CYCLES = 60


class rackhd_stack_init(unittest.TestCase):
    def test01_set_auth_user(self):
        auth_json = open('auth.json', 'w')
        auth_json.write('{"username":"' + fit_common.fitcreds()["api"][0]["admin_user"] + '", "password":"' +
                        fit_common.fitcreds()["api"][0]["admin_pass"] + '", "role":"Administrator"}')
        auth_json.close()
        try:
            # add first user to remote rackhd directly
            return_code = ""
            rackhd_hostname = fit_common.fitargs()['rackhd_host']
            set_auth_url = "https://" + rackhd_hostname + ":" + str(fit_common.fitports()['https']) + "/api/2.0/users"
            rc = fit_common.restful(url_command=set_auth_url, rest_action="post", rest_payload=json.load(open('auth.json')))
            return_code = str(rc['status'])
        except Exception as e:
            log.info_5("ALERT: RackHD is not in localhost, will set first user through ssh{0}".format(e))
        if return_code != '201':
            log.info_5("ALERT: Can't set first user to RackHD https port directly, will set it through ssh")
            # ssh login to rackhd and add first user to localhost rackhd
            fit_common.remote_shell('rm auth.json')
            fit_common.scp_file_to_ora('auth.json')
            rc = fit_common.remote_shell("curl -ks -X POST -H 'Content-Type:application/json' https://localhost:" +
                                         str(fit_common.fitports()['https']) + "/api/2.0/users -d @auth.json")
            if rc['exitcode'] != 0:
                log.info_5("ALERT: Auth admin user not set! Please manually set the admin user account if required.")

    def test02_preload_sku_packs(self):
        log.info_5("**** Downloading SKU packs from GitHub")
        subprocess.call("rm -rf temp.sku; rm -rf on-skupack", shell=True)
        os.mkdir("on-skupack")
        # download all SKU repos and merge into on-skupack
        for url in fit_common.fitskupack():
            log.info_5("**** Cloning SKU Packs from " + url)
            subprocess.call("git clone " + url + " temp.sku", shell=True)
            subprocess.call('cp -R temp.sku/* on-skupack; rm -rf temp.sku', shell=True)
        # build build SKU packs
        for subdir, dirs, files in os.walk('on-skupack'):
            for skus in dirs:
                if skus not in ["debianstatic", ".git"] and os.path.isfile('on-skupack/' + skus + '/config.json'):
                    subprocess.call("cd on-skupack;mkdir -p " + skus + "/tasks " + skus + "/static " +
                                    skus + "/workflows " + skus + "/templates", shell=True)
                    subprocess.call("cd on-skupack; ./build-package.bash " +
                                    skus + " " + skus + " >/dev/null 2>&1", shell=True)
            break
        # upload SKU packs to ORA
        log.info_5("**** Loading SKU Packs to server")
        for subdir, dirs, files in os.walk('on-skupack/tarballs'):
            for skupacks in files:
                log.info_5("**** Loading SKU Pack for " + skupacks)
                file = open(fit_common.TEST_PATH + "on-skupack/tarballs/" + skupacks)
                fit_common.rackhdapi("/api/2.0/skus/pack", action="binary-post", payload=file.read())
                file.close()
            break
        # check SKU directory against source files
        error_message = ""
        skulist = json.dumps(fit_common.rackhdapi("/api/2.0/skus")['json'])
        for subdir, dirs, files in os.walk('on-skupack'):
            for skus in dirs:
                if skus not in ["debianstatic", ".git", "packagebuild", "tarballs"] and \
                   os.path.isfile('on-skupack/' + skus + '/config.json'):
                    try:
                        configfile = json.loads(open("on-skupack/" + skus + "/config.json").read())
                        # check if sku pack got installed
                        if configfile['name'] not in skulist:
                            log.error("FAILURE - Missing SKU: " + configfile['name'])
                            error_message += "  Missing SKU: " + configfile['name']
                    except:
                        # Check is the sku pack config.json file is valid format, fails skupack install if invalid
                        log.error("FAILURE - Corrupt config.json in SKU Pack: " + str(skus) + " - not loaded")
                        error_message += "  Corrupt config.json in SKU Pack: " + str(skus)
            break
        self.assertEqual(error_message, "", error_message)

    def test03_preload_default_sku(self):
        # Load default SKU for unidentified compute nodes
        payload = {"name": "Unidentified-Compute", "rules": [{"path": "bmc.IP Address"}]}
        api_data = fit_common.rackhdapi("/api/2.0/skus", action='post', payload=payload)
        self.assertIn(api_data['status'], [201, 409],
                      'Incorrect HTTP return code, expecting 201 or 409, got ' + str(api_data['status']))

    def test04_power_on_nodes(self):
        # This powers on nodes via PDU or, if no PDU, power cycles nodes via IPMI to start discovery
        # ServerTech PDU case
        if pdu_lib.check_pdu_type() != "Unknown":
            log.info_5('**** PDU found, powering on PDU outlets')
            self.assertTrue(pdu_lib.pdu_control_compute_nodes("on"), 'Failed to power on all outlets')
            # Wait about 30 seconds for the outlets to all come on and nodes to DHCP
            fit_common.countdown(30)
        # no PDU case
        else:
            log.info_5('**** No supported PDU found, restarting nodes using IPMI.')
            # Power cycle all nodes via IPMI, display warning if no nodes found
            if fit_common.power_control_all_nodes("off") == 0:
                log.info_5('**** No BMC IP addresses found in arp table, continuing without node restart.')
            else:
                # power on all nodes under any circumstances
                fit_common.power_control_all_nodes("on")

    # Optionally install control switch node if present
    @unittest.skipUnless("control" in fit_common.fitcfg(), "")
    def test05_discover_control_switch_node(self):
        log.info_5("**** Creating control switch node.")
        payload = {"type": "switch",
                   "name": "Control",
                   "autoDiscover": True,
                   "obms": [{"service": "snmp",
                             "config": {"host": fit_common.fitcfg()['control'],
                                        "community": fit_common.fitcreds()['snmp'][0]['community']}}]}
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got ' +
                         str(api_data['status']))

    # Optionally install data switch node if present
    @unittest.skipUnless("data" in fit_common.fitcfg(), "")
    def test06_discover_data_switch_node(self):
        log.info_5("**** Creating data switch node.")
        payload = {"type": "switch",
                   "name": "Data",
                   "autoDiscover": True,
                   "obms": [{"service": "snmp",
                             "config": {"host": fit_common.fitcfg()['data'],
                                        "community": fit_common.fitcreds()['snmp'][0]['community']}}]}
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got ' +
                         str(api_data['status']))

    # Optionally install PDU node if present
    @unittest.skipUnless("pdu" in fit_common.fitcfg(), "")
    def test07_discover_pdu_node(self):
        log.info_5("**** Creating PDU node.")
        payload = {"type": "pdu",
                   "name": "PDU",
                   "autoDiscover": True,
                   "obms": [{"service": "snmp",
                             "config": {"host": fit_common.fitcfg()['pdu'],
                                        "community": fit_common.fitcreds()['snmp'][0]['community']}}]}
        api_data = fit_common.rackhdapi("/api/2.0/nodes/", action='post', payload=payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expecting 201, got ' +
                         str(api_data['status']))

    def test08_check_compute_nodes(self):
        log.info_5("**** Waiting for compute nodes.")
        c_index = 0
        for c_index in range(0, MAX_CYCLES):
            if "compute" in fit_common.rackhdapi("/api/2.0/nodes")['text']:
                break
            else:
                time.sleep(30)
        self.assertLess(c_index, MAX_CYCLES - 1, "No compute nodes found.")

    def test09_check_discovery(self):
        log.info_5("**** Waiting for node Discovery to complete.\n",)
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
        for _ in range(0, max_time):
            nodes_data = fit_common.rackhdapi("/api/2.0/nodes")
            if nodes_data['status'] == 200 and len(nodes_data['json']) > 0:
                # if there are nodes present, determine if discovery has completed on them
                discovery_complete = True
                for node in nodes_data['json']:
                    if node['type'] == 'compute':
                        self.assertIn('id', node, 'node does not contain id')
                        node_id = node['id']
                        # determine if there are any active worlflows. If so, discovery not completed
                        if fit_common.check_active_workflows(node_id):
                            discovery_complete = False
                            break
                if discovery_complete:
                    return True
                time.sleep(10)
        return False

    def test10_apply_obm_settings(self):
        log.info_5("**** Apply OBM setting to compute nodes.")
        self.assertTrue(fit_common.apply_obm_settings(), "OBM settings failed.")

    @unittest.skipUnless("bmc" in fit_common.fitcfg(), "")
    @unittest.skip("Skipping 'test10_add_management_server' bug RAC-4063")
    def test11_add_management_server(self):
        log.info_5("**** Creating management server.")
        usr = ""
        pwd = ""
        # find correct BMC passwords from credentials list
        for creds in fit_common.fitcreds()['bmc']:
            if fit_common.remote_shell('ipmitool -I lanplus -H ' + fit_common.fitcfg()['bmc'] +
                                       ' -U ' + creds['username'] + ' -P ' +
                                       creds['password'] + ' fru')['exitcode'] == 0:
                usr = creds['username']
                pwd = creds['password']
        # create management node using these creds
        if usr != "" and pwd != "":
            payload = {"name": "Management Server " + str(time.time()),
                       "type": "mgmt",
                       "autoDiscover": True,
                       "obms": [{"service": "ipmi-obm-service",
                                 "config": {"host": fit_common.fitcfg()['bmc'],
                                            "user": usr,
                                            "password": pwd}}]}
            api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=payload)
            self.assertEqual(api_data['status'], 201,
                             'Incorrect HTTP return code, expecting 201, got ' + str(api_data['status']))
        else:
            self.fail("Unable to contact management server BMC, skipping MGMT node create")

    def test12_check_pollers(self):
        log.info_5("**** Waiting for pollers.")
        # Determine if there are any pollers present. If the return value is true, there are pollers
        # active. If the return value is false, pollers are not active.
        # Wait 10 minutes ( MAX_CYCLES * 10 seconds) for this to occur.
        self.assertTrue(self.check_for_active_pollers(MAX_CYCLES), 'No pollers')
        log.info_5("**** Waiting for pollers data.")
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
        for _ in range(0, max_time):
            api_data = fit_common.rackhdapi('/api/2.0/pollers')
            if len(api_data['json']) > 0:
                return True
            time.sleep(30)
        return False

    def check_for_active_poller_data(self, max_time):
        '''
        Determine if all poller have data.
        :param    Time to wait (in 10 second intervals)
        :return:  True  - Poller have data
                  False - Not all poller have data
        '''
        poller_list = []
        api_data = fit_common.rackhdapi('/api/2.0/pollers')
        if api_data:
            # set up a list of poller ids
            for index in api_data['json']:
                poller_list.append(index['id'])
            if poller_list != []:
                for _ in range(0, max_time):
                    # move backwards through the list allowing completed poller ids to be popped
                    # off the list
                    for i in reversed(range(len(poller_list))):
                        id = poller_list[i]
                        poll_data = fit_common.rackhdapi("/api/2.0/pollers/" + id + "/data/current")
                        # Check if data current returned 200 and data in the poll, if so, remove from list
                        if poll_data['status'] == 200 and len(poll_data['json']) != 0:
                            poller_list.pop(i)
                    if poller_list == []:
                        # return when all pollers look good
                        return True
                    time.sleep(10)
        if poller_list != []:
            log.error("Poller IDs with error or no data: {}".format(json.dumps(poller_list, indent=4)))
        return False

    def test99_display_node_list_discovery_data(self):
        # This test displays a list of the nodes along with
        # the associated BMC, RMM, and OBM settings for the discovered compute nodes
        mondata = fit_common.rackhdapi("/api/2.0/nodes")
        nodes = mondata['json']
        result = mondata['status']

        if result == 200:
            print "\nNODE INVENTORY"
            print "\nNumber of nodes found: " + str(len(nodes)) + "\n"
            i = 0
            for node in nodes:
                i += 1
                print ""
                nn = node["id"]
                print "Node {0}: {1}".format(str(i), nn)
                # Check type of node and display info
                nodetype = node['type']
                if nodetype != "compute":
                    print "Node Type: ", nodetype
                    if nodetype == "enclosure":
                        print "Node Name: ", node['name']
                        nodelist = test_api_utils.get_relations_for_node(nn)
                        if nodelist:
                            print "Nodes contained in this enclosure: ", nodelist
                        else:
                            print "No Nodes found in this enclosure"
                else:
                    # If compute node, display BMC, RMM and IP info
                    nodetype = test_api_utils.get_rackhd_nodetype(nn)
                    print "Compute Node Type: ", nodetype
                    enclosure = test_api_utils.get_relations_for_node(nn)
                    if enclosure:
                        print "In Enclosure: ", enclosure[0]
                    else:
                        print "Not associated with a monorail enclosure"
                    # try to get the BMC info from the catalog
                    monurl = "/api/2.0/nodes/" + nn + "/catalogs/bmc"
                    mondata = fit_common.rackhdapi(monurl, action="get")
                    catalog = mondata['json']
                    bmcresult = mondata['status']
                    print "BMC MAC Address",
                    print "\tBMC IP Address",
                    print "\tBMC IP Source",
                    print "\tRMM MAC Address",
                    print "\tRMM IP Address",
                    print "\tRMM IP Source",
                    print "\tOBM Host",
                    print "\t\tOBM User"
                    if bmcresult != 200:
                        print "Error on catalog/bmc command",
                    else:
                        print catalog["data"]["MAC Address"],
                        print "\t" + catalog["data"]["IP Address"],
                        print "\t" + catalog["data"]["IP Address Source"],
                    # Get RMM info from the catalog, if present
                    rmmurl = "/api/2.0/nodes/" + nn + "/catalogs/rmm"
                    rmmdata = fit_common.rackhdapi(rmmurl, action="get")
                    rmmcatalog = rmmdata['json']
                    rmmresult = rmmdata['status']
                    if rmmresult != 200:
                        print "\tNo RMM catalog entry.\t\t\t\t\t",
                    else:
                        print "\t" + rmmcatalog["data"].get("MAC Address", "-"),
                        print "\t" + rmmcatalog["data"].get("IP Address", "-"),
                        print "\t" + rmmcatalog["data"].get("IP Address Source", "-") + "\t",

                    nodeurl = "/api/2.0/nodes/" + nn
                    nodedata = fit_common.rackhdapi(nodeurl, action="get")
                    nodeinfo = nodedata['json']
                    result = nodedata['status']
                    if result != 200:
                        print "Error on node command" + nodeurl + ", http response:  " + result
                    else:
                        # Check BMC IP vs OBM IP setting
                        try:
                            obmlist = nodeinfo["obms"]
                        except:
                            print "ERROR: Node has no OBM settings configured"
                        else:
                            try:
                                obmurl = obmlist[0]['ref']
                                obmdata = fit_common.rackhdapi(obmurl, action="get")
                            except:
                                print "Invalid or empty OBM setting"
                            else:
                                print obmdata['json']["config"].get("host", "Error: No Host in obmdata"),
                                print "\t" + obmdata['json']["config"].get("user", "Error: No User defined!")
        else:
            print "Cannot get RackHD nodes from stack, http response code: ", result


if __name__ == '__main__':
    unittest.main()
