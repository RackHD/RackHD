'''
Copyright 2016, EMC, Inc.

Author(s):

Test for switch telemetry.
'''

import fit_path  # NOQA: unused import
import sys
import subprocess
import json
import time

import fit_common


# POLLS is number of loops performed per test case where we are retrieving polled data
POLLS = 1

NODELIST = []

def get_switches():
    # returns a list with valid node IDs that match ARGS_LIST.sku in 'Name' or 'Model' field
    # and matches node BMC MAC address in ARGS_LIST.obmmac if specified
    # Otherwise returns list of all IDs that are not 'Unknown' or 'Unmanaged'
    nodelist = []

    # check if user specified a single nodeid to run against
    # user must know the nodeid and any check for a valid nodeid is skipped
    nodeid = fit_common.fitargs()['nodeid']
    if nodeid != 'None':
        nodelist.append(nodeid)
    else:
        catalog = fit_common.rackhdapi('/api/1.1/nodes')
        for nodeentry in catalog['json']:
            if nodeentry['type'] == 'switch':
                nodelist.append(nodeentry['id'])
    return nodelist

NODELIST = get_switches()

def get_rackhd_nodetype(nodeid):
    nodetype = ""
    # get the node info
    mondata = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid)
    if mondata['status'] != 200:
        print "Incorrect HTTP return code on nodeid, expected 200, received: {}".format(mondata['status'])
    else:
        # get the sku id contained in the node
        sku = mondata['json'].get("sku", 0)
        if sku != 0:
            skudata = fit_common.rackhdapi("/api/1.1/skus/" + sku)
            if skudata['status'] != 200:
                print "Incorrect HTTP return code on sku, expected 200, received: {}".format(skudata['status'])
            else:
                nodetype = mondata['json'].get("name","")
        else:
            nodetype = mondata['json'].get("name","")
            print ("Error: nodeid {} did not return a valid sku in get_rackhd_nodetype".format(nodeid))
    return nodetype


from nose.plugins.attrib import attr
@attr(all=True, regression=True)
@fit_common.unittest.skipIf(NODELIST == [],"No switches defined, skipping test.")
class rackhd11_switch_telemetry(fit_common.unittest.TestCase):
    def test_poller_snmp_state(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display poller snmp-interface-state."
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(mon_data['status']))

            poller_list = []
            poller_test = "snmp-interface-state"
            for item in mon_data['json']:
                if item['config']['metric'] == poller_test:
                    poller_list.append(item['id'])
            if fit_common.VERBOSITY >= 2:
                print "Poller list", poller_list
            self.assertNotEquals(poller_list, [], "Poller {0} not in list of pollers".format(poller_test))

            pollertime = i = 0
            while i < POLLS:
                if POLLS > 1 and pollertime:
                    print "sleeping " + str(pollertime) + " seconds"
                    time.sleep(pollertime)

                # for the list of poller ids, get the poller data and check the fields exist
                for poller_id in poller_list:
                    poller = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id)
                    self.assertIn(poller['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(poller['status']))
                    pollerdata = poller['json']

                    # check required fields and grab the poller times
                    self.assertGreater(pollerdata['pollInterval'], 0, 'pollInterval field error')
                    poller_interval = pollerdata['pollInterval']
                    pollertime = poller_interval / 1000
                    if fit_common.VERBOSITY >= 2:
                        print "pollerInterval", poller_interval
                        print "PollerData metric: ", pollerdata['config']['metric']
                        print "NextScheduled poll: ", pollerdata['nextScheduled']
                        print "PollerTime: ", pollertime

                    # get the current readings from the switch for this poller
                    pollcurrent = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id + "/data/current")
                    self.assertIn(pollcurrent['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(pollcurrent['status']))

                    # dump the world
                    if fit_common.VERBOSITY >= 3:
                        print json.dumps(pollcurrent['json'], indent=4)

                    # display the interfaces that are UP
                    if fit_common.VERBOSITY >= 2:
                        result = pollcurrent['json'][0]['result']
                        for key, value in result.items():
                            if value.get("state") == "up" and fit_common.VERBOSITY >= 2:
                                print "IF: {} Status: {}".format(key, value)
                i += 1


    def test_poller_bandwidth_util(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display snmp-interface-bandwidth-utilization."
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(mon_data['status']))

            poller_list = []
            poller_test = "snmp-interface-bandwidth-utilization"
            for item in mon_data['json']:
                if item['config']['metric'] == poller_test:
                    poller_list.append(item['id'])
            if fit_common.VERBOSITY >= 2:
                print "Poller list", poller_list
            self.assertNotEquals(poller_list, [], "Poller {0} not in list of pollers".format(poller_test))

            pollertime = i = 0
            while i < POLLS:
                if POLLS > 1 and pollertime:
                    print "sleeping " + str(pollertime) + " seconds"
                    time.sleep(pollertime)

                # for the list of poller ids, get the poller data and check the fields exist
                for poller_id in poller_list:
                    poller = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id)
                    self.assertIn(poller['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(poller['status']))
                    pollerdata = poller['json']

                    # check required fields and grab the poller times
                    self.assertGreater(pollerdata['pollInterval'], 0, 'pollInterval field error')
                    poller_interval = pollerdata['pollInterval']
                    pollertime = poller_interval / 1000
                    if fit_common.VERBOSITY >= 2:
                        print "pollerInterval", poller_interval
                        # metric is the name of the poller
                        print "PollerData metric: ", pollerdata['config']['metric']
                        print "NextScheduled poll: ", pollerdata['nextScheduled']
                        print "PollerTime: ", pollertime

                    # get the current readings from the switch for this poller
                    pollcurrent = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id + "/data/current")
                    self.assertIn(pollcurrent['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(pollcurrent['status']))

                    # dump the world
                    if fit_common.VERBOSITY >= 3:
                        print json.dumps(pollcurrent['json'], indent=4)

                    # display the interfaces that are UP
                    if fit_common.VERBOSITY >= 2:
                        result = pollcurrent['json'][0]['result']
                        for key, value in result.items():
                            if value.get("inputUtilization") != None and fit_common.VERBOSITY >= 2:
                                print "IF: {} Utilization: {}".format(key, value)
                i += 1

    def test_snmp_memory_util(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display poller snmp-memory-usage."
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(mon_data['status']))

            poller_list = []
            poller_test = "snmp-memory-usage"
            for item in mon_data['json']:
                if item['config']['metric'] == poller_test:
                    poller_list.append(item['id'])
            if fit_common.VERBOSITY >= 2:
                print "Poller list", poller_list
            self.assertNotEquals(poller_list, [], "Poller {0} not in list of pollers".format(poller_test))

            pollertime = i = 0
            while i < POLLS:
                if POLLS > 1 and pollertime:
                    print "sleeping " + str(pollertime) + " seconds"
                    time.sleep(pollertime)

                # for the list of poller ids, get the poller data and check the fields exist
                for poller_id in poller_list:
                    poller = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id)
                    self.assertIn(poller['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(poller['status']))
                    pollerdata = poller['json']

                    # check required fields and grab the poller times
                    self.assertGreater(pollerdata['pollInterval'], 0, 'pollInterval field error')
                    poller_interval = pollerdata['pollInterval']
                    pollertime = poller_interval / 1000
                    if fit_common.VERBOSITY >= 2:
                        print "pollerInterval", poller_interval
                        print "PollerData metric: ", pollerdata['config']['metric']
                        print "NextScheduled poll: ", pollerdata['nextScheduled']
                        print "PollerTime: ", pollertime

                    # get the current readings from the switch for this poller
                    pollcurrent = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id + "/data/current")
                    self.assertIn(pollcurrent['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(pollcurrent['status']))

                    # display the snmp memory usage data from the switch
                    if fit_common.VERBOSITY >= 2  and fit_common.VERBOSITY >= 2:
                        result = pollcurrent['json'][0]['result']
                        print json.dumps(result, indent=4)
                i += 1

    def test_snmp_processor_load(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the snmp-processor-load."
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(mon_data['status']))

            poller_list = []
            poller_test = "snmp-processor-load"
            for item in mon_data['json']:
                if item['config']['metric'] == poller_test:
                    poller_list.append(item['id'])
            if fit_common.VERBOSITY >= 2:
                print "Poller list", poller_list
            self.assertNotEquals(poller_list, [], "Poller {0} not in list of pollers".format(poller_test))

            pollertime = i = 0
            while i < POLLS:
                if POLLS > 1 and pollertime:
                    print "sleeping " + str(pollertime) + " seconds"
                    time.sleep(pollertime)

                # for the list of poller ids, get the poller data and check the fields exist
                for poller_id in poller_list:
                    poller = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id)
                    self.assertIn(poller['status'], [200], "Incorrect HTTP return code")
                    pollerdata = poller['json']
                    poller_interval = pollerdata['pollInterval']
                    pollertime = poller_interval / 1000
                    if fit_common.VERBOSITY >= 2:
                        # metric is the name of the poller
                        print "PollerData metric: ", pollerdata['config']['metric']
                        print "NextScheduled poll: ", pollerdata['nextScheduled']
                        print "PollerTime: ", pollertime

                    # get the current readings from the switch for this poller
                    pollcurrent = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id + "/data/current")
                    self.assertIn(pollcurrent['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(pollcurrent['status']))

                    # display the snmp reported switch processor load
                    if fit_common.VERBOSITY >= 2 and fit_common.VERBOSITY >= 2:
                        result = pollcurrent['json'][0]['result']
                        print json.dumps(result, indent=4)
                i += 1

    def test_display_interfaces(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display switch ports that are connected and UP"
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(mon_data['status']))

            poller_list = []
            poller_list_util = []
            for item in mon_data['json']:
                if item['config']['metric'] == "snmp-interface-state":
                    poller_list.append(item['id'])
                if item['config']['metric'] == "snmp-interface-bandwidth-utilization":
                    poller_list_util.append(item['id'])
            if fit_common.VERBOSITY >= 2:
                print "Poller snmp-interface-state: ", poller_list
            self.assertNotEquals(poller_list, [], "Poller {0} not in list of pollers".format("snmp-interface-state"))

            # display the switch ports reporting UP
            for poller_id in poller_list:
                pollcurrent = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id + "/data/current")
                self.assertIn(pollcurrent['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(pollcurrent['status']))
                if fit_common.VERBOSITY >= 5:
                    print json.dumps(pollcurrent['json'], indent=4)
                result = pollcurrent['json'][0]['result']
                for key, value in result.items():
                    if value.get("state") == "up" and fit_common.VERBOSITY >= 2:
                        print "IF: {} Status: {}".format(key, value)

            # display the switch ports reporting any utilization
            if fit_common.VERBOSITY >= 2:
                print "\nPoller snmp-interface-bandwidth-utilization: ", poller_list_util
            self.assertNotEquals(poller_list_util, [], "Poller {0} not in list of pollers".format("snmp-interface-bandwidth-utilizatoni"))
            for poller_id in poller_list_util:
                pollcurrent = fit_common.rackhdapi("/api/1.1/pollers/"+ poller_id + "/data/current")
                self.assertIn(pollcurrent['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(pollcurrent['status']))
                if fit_common.VERBOSITY >= 5:
                    print json.dumps(pollcurrent['json'], indent=4)
                result = pollcurrent['json'][0]['result']
                for key, value in result.items():
                    if value.get("inputUtilization") != None and fit_common.VERBOSITY >= 2:
                        print "IF: {} Utilization: {}".format(key, value)

if __name__ == '__main__':
    fit_common.unittest.main()
