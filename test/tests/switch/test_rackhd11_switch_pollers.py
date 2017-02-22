'''
Copyright 2016, EMC, Inc.

Author(s):

FIT test script template
'''

import fit_path  # NOQA: unused import
import sys
import subprocess
import pprint

import fit_common
import test_api_utils

# LOCAL

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
        sku = mondata['json'].get("sku")
        if sku:
            skudata = fit_common.rackhdapi("/api/1.1/skus/" + sku)
            if skudata['status'] != 200:
                print "Incorrect HTTP return code on sku, expected 200, received: {}".format(skudata['status'])
            else:
                nodetype = mondata['json'].get("name")
        else:
            nodetype = mondata['json'].get("name")
            print "nodeid {} did not return a valid sku in get_rackhd_nodetype".format(nodeid)
    return nodetype

from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
@fit_common.unittest.skipIf(NODELIST == [],"No switches defined, skipping test.")
class rackhd11_switch_pollers(fit_common.unittest.TestCase):

    def test_get_id_pollers(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the poller data per node."
            print "\t{0}".format(msg)

        for node in NODELIST:
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code")
            for item in mon_data['json']:
                # check required fields
                self.assertGreater(item['pollInterval'], 0, 'pollInterval field error')
                for subitem in ['node', 'config', 'createdAt', 'id', 'name', 'config']:
                    self.assertIn(subitem, item, subitem + ' field error')
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                poll_data = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id)
                if fit_common.VERBOSITY >= 2:
                    print "\nPoller: " + poller + " ID: " + str(poller_id)
                    print fit_common.json.dumps(poll_data['json'], indent=4)

    def test_verify_poller_headers(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Verify header data reported on the poller"
            print "\t{0}".format(msg)

        for node in NODELIST:
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code")
            nodetype = get_rackhd_nodetype(node)
            if fit_common.VERBOSITY >= 2:
                print "\nNode: {} Type: {}".format(node, nodetype)
            # Run test against managed nodes only
            if nodetype != "unknown" and nodetype != "Unmanaged":
                poller_dict = test_api_utils.get_supported_pollers(node)

                for poller in poller_dict:
                    poller_id = poller_dict[poller]["poller_id"]
                    poller_data = test_api_utils.get_poller_data_by_id(poller_id)
                    if fit_common.VERBOSITY >= 3:
                        print "\nPoller: " + poller + " ID: " + str(poller_id)
                        print fit_common.json.dumps(poller_data, indent=4)

    def test_verify_poller_data(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Check number of polls being kept for poller ID"
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            nodetype = get_rackhd_nodetype(node)
            # Run test against managed nodes only
            if nodetype != "unknown" and nodetype != "Unmanaged":
                poller_dict = test_api_utils.get_supported_pollers(node)

                for poller in poller_dict:
                    poller_id = poller_dict[poller]["poller_id"]
                    poller_data = test_api_utils.get_poller_data_by_id(poller_id)
                    poll_len = len(poller_data)
                    if fit_common.VERBOSITY >= 2:
                        print "\nPoller: " + poller + " ID: " + str(poller_id)
                        print "Number of polls for "+ str(poller_id) + ": " + str(len(poller_data))
                    self.assertLessEqual(poll_len, 10, 'Number of cached polls should not exceed 10')

    def test_get_current_poller_data(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display most current data from poller"
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            nodetype = get_rackhd_nodetype(node)
            # Run test against managed nodes only
            if nodetype != "unknown" and nodetype != "Unmanaged":
                poller_dict = test_api_utils.get_supported_pollers(node)

                for poller in poller_dict:
                    poller_id = poller_dict[poller]["poller_id"]
                    if fit_common.VERBOSITY >= 2:
                        print "\nPoller: " + poller + " ID: " + str(poller_id)
                    monurl = "/api/1.1/pollers/" + str(poller_id) + "/data/current"
                    mondata = fit_common.rackhdapi(url_cmd=monurl)
                    if fit_common.VERBOSITY >= 2:
                        print fit_common.json.dumps(mondata, indent=4)

    def test_get_poller_status_timestamp(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display status and timestamp from current poll"
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            nodetype = get_rackhd_nodetype(node)
            # Run test against managed nodes only
            if nodetype != "unknown" and nodetype != "Unmanaged":
                poller_dict = test_api_utils.get_supported_pollers(node)

                for poller in poller_dict:
                    poller_id = poller_dict[poller]["poller_id"]
                    if fit_common.VERBOSITY >= 2:
                        print "\nPoller: " + poller + " ID: " + str(poller_id)
                    monurl = "/api/1.1/pollers/" + str(poller_id) + "/data/current"
                    mondata = fit_common.rackhdapi(url_cmd=monurl)
                    print "Return status", mondata['status']
                    if mondata['status'] == 200:
                        if fit_common.VERBOSITY >= 2:
                            print "Timestamp:", mondata['json'][0]['timestamp']
                            print fit_common.json.dumps(mondata['json'][0], indent=4)

    def test_verify_poller_error_counter(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Check for Poller Errors"
            print "\t{0}".format(msg)
        errorlist = []
        for node in NODELIST:
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code")
            for item in mon_data['json']:
                # check required fields
                self.assertGreater(item['pollInterval'], 0, 'pollInterval field error')
                for subitem in ['node', 'config', 'createdAt', 'id', 'name', 'config', 'updatedAt']:
                    self.assertIn(subitem, item, subitem + ' field error')
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                poll_data = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id)
                poll_fails = poll_data['json'].get('failureCount', 0)
                if poll_fails != 0:
                    errorlist.append("Node: {} Poller: {} {} reported {} failureCount".format(node,
                                                                                              poller,
                                                                                              poller_id,
                                                                                              poll_fails))
        if errorlist != []:
            print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reported in Pollers")
        else:
            if fit_common.VERBOSITY >= 2:
                print ("No Poller errors found")

    def test_get_nodes_id_pollers(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the poller updated-at per node."
            print "\t{0}".format(msg)

        node = 0
        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code")
            for item in mon_data['json']:
                # check required fields
                self.assertGreater(item['pollInterval'], 0, 'pollInterval field error')
                for subitem in ['node', 'config', 'createdAt', 'id', 'name', 'config', 'updatedAt']:
                    self.assertIn(subitem, item, subitem + ' field error')
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                poll_data = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id)
                if fit_common.VERBOSITY >= 2:
                    print "\nPoller: " + poller + " ID: " + str(poller_id)
                    pprint.pprint("Created At: {}".format(poll_data['json']['createdAt']))
                    pprint.pprint("Updated At: {}".format(poll_data['json']['updatedAt']))

    def test_check_poller_interval(self):
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the poller interval."
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                print "\nNode: ", node
            mon_data = fit_common.rackhdapi("/api/1.1/nodes/" + node + "/pollers")
            self.assertIn(mon_data['status'], [200], "Incorrect HTTP return code, expected 200, got {}".format(mon_data['status']))

            poller_list = []
            if fit_common.VERBOSITY >= 2:
                print fit_common.json.dumps(mon_data['json'], indent=4)
            for item in mon_data['json']:
                poller_list.append(item['id'])

            for poller_id in poller_list:
                poller = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id )
                self.assertIn(poller['status'], [200], "Incorrect HTTP return code")
                pollerdata = poller['json']

                # check required fields
                self.assertGreater(pollerdata['pollInterval'], 0, 'pollInterval field error')
                poller_interval = pollerdata['pollInterval']
                pollertime = poller_interval / 1000
                if fit_common.VERBOSITY >= 2:
                    print "pollerInterval", poller_interval
                    print pollerdata['config'].get('metric', "")
                    print pollerdata.get('nextScheduled', "")
                    print pollertime

                pollcurrent = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id + "/data/current" )
                self.assertIn(pollcurrent['status'], [200], "Incorrect HTTP return code")
                if fit_common.VERBOSITY >= 2:
                    print pollcurrent

if __name__ == '__main__':
    fit_common.unittest.main()

