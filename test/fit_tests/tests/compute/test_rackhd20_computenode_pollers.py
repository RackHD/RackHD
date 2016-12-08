'''
Copyright 2016, EMC, Inc.

Author(s):

This test checks pollers under API 1.1
'''


import sys
import subprocess

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common
import test_api_utils

# LOCAL


NODELIST = fit_common.node_select()
if NODELIST == []:
    print "No nodes found on stack"
    sys.exit(255)


def get_rackhd_nodetype(nodeid):
    nodetype = ""
    # get the node info
    mondata = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid)
    if mondata['status'] != 200:
        print "Incorrect HTTP return code on nodeid, expected 200, received: {}".format(mondata['status'])
    else:
        # get the sku id contained in the node
        sku = mondata['json'].get("sku")
        sku = sku.split("/")[-1]
        if sku:
            skudata = fit_common.rackhdapi("/api/2.0/skus/" + sku)
            if skudata['status'] != 200:
                print "Error: Incorrect HTTP return code on sku, expected 200, received: {}".format(skudata['status'])
            else:
                nodetype = skudata['json'].get("name")
        else:
            print "Error: nodeid {} did not return a valid sku in get_rackhd_nodetype{}".format(nodeid, sku)
    return nodetype

from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_computenode_pollers(fit_common.unittest.TestCase):
    def test_1_verify_pollers(self):
        msg = "Description: Check pollers created for node"
        if fit_common.VERBOSITY >= 2:
            print "\t{0}".format(msg)

        errorlist = []
        poller_list = ['driveHealth', 'sel', 'chassis', 'selInformation', 'sdr', 'selEntries']
        if fit_common.VERBOSITY >= 2:
            print "Expected Pollers for a Node: ".format(poller_list)
        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                nodetype = get_rackhd_nodetype(node)
                print "\nNode: {}  Type: {}".format(node, nodetype)
            mondata = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertIn(mondata['status'], [200], "Incorrect HTTP return code, expecting 200, received {}".format(mondata['status']))

            poller_dict = test_api_utils.get_supported_pollers(node)
            if set(poller_list) == set(poller_dict):
                if fit_common.VERBOSITY >= 2:
                    print "Expected pollers instantiated on node"
                if fit_common.VERBOSITY >= 3:
                    print "Poller list retreived", poller_dict
            else:
                if list(set(poller_list) - set(poller_dict)):
                    errorlist.append("Error: Node {0} Pollers not running {1}".format(node, list(set(poller_list) - set(poller_dict))))
                if list(set(poller_dict) - set(poller_list)):
                    errorlist.append("Error: Node {0} Unexpected Pollers running {1}".format(node, list(set(poller_dict) - set(poller_list))))

        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reported.")


    def test_2_pollers_by_id(self):
        msg = "Description: Display the poller data per node."
        if fit_common.VERBOSITY >= 2:
            print "\t{0}".format(msg)

        errorlist = []
        poller_list = ['driveHealth', 'sel', 'chassis', 'selInformation', 'sdr', 'selEntries']
        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                nodetype = get_rackhd_nodetype(node)
                print "Node: {}  Type: {}".format(node, nodetype)
            mondata = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertIn(mondata['status'], [200], "Incorrect HTTP return code, expecting 200, received {}".format(mondata['status']))

            # check required fields
            for item in mondata['json']:
                if item['pollInterval'] == 0:
                    errorlist.append("Node: {} pollInterval field error: {}".format(node, item['pollInterval']))
                for subitem in ['node', 'config', 'createdAt', 'id', 'name', 'config']:
                    if subitem not in item:
                        errorlist.append("Node: {} field error: {}".format(node, subitem))

            # display poller data for the node
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                if fit_common.VERBOSITY >= 2:
                    print "Poller: {}  ID: {} ".format(poller, str(poller_id))
                poll_data = fit_common.rackhdapi("/api/2.0/pollers/" + poller_id)
                if fit_common.VERBOSITY >= 3:
                    print fit_common.json.dumps(poll_data.get('json', ""), indent=4)

        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reported.")

    def test_3_poller_headers(self):
        msg = "Description: Verify header data reported on the poller"
        if fit_common.VERBOSITY >= 2:
            print "\t{0}".format(msg)

        errorlist = []
        for node in NODELIST:
            mondata = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertIn(mondata['status'], [200], "Incorrect HTTP return code, expecting 200, received {}".format(mondata['status']))
            if fit_common.VERBOSITY >= 2:
                nodetype = get_rackhd_nodetype(node)
                print "\nNode: {} Type: {}".format(node, nodetype)

            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                if fit_common.VERBOSITY >= 2:
                    print "Poller: {}  ID: {} ".format(poller, str(poller_id))
                poller_data = test_api_utils.get_poller_data_by_id(poller_id)
                if poller_data == []:
                    errorlist.append("Error: Node {} Poller ID {}, {} failed to return any data".format(node, poller_id, poller))
                if fit_common.VERBOSITY >= 3:
                    print fit_common.json.dumps(poller_data, indent=4)

        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reported.")

    def test_4_poller_default_cache(self):
        msg = "Description: Check number of polls being kept for poller ID"
        if fit_common.VERBOSITY >= 2:
            print "\t{0}".format(msg)

        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                nodetype = get_rackhd_nodetype(node)
                print "Node: {}  Type: {}".format(node, nodetype)
        errorlist = []
        for node in NODELIST:
            nodetype = get_rackhd_nodetype(node)
            if fit_common.VERBOSITY >= 2:
                print "\nNode: {} Type: {}".format(node, nodetype)

            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                poller_data = test_api_utils.get_poller_data_by_id(poller_id)
                poll_len = len(poller_data)
                if fit_common.VERBOSITY >= 2:
                    print "Poller: {}  ID: {} ".format(poller, str(poller_id))
                    print "Number of polls for "+ str(poller_id) + ": " + str(len(poller_data))
                if poll_len > 10:
                    errorlist.append('Error: Poller {} ID: {} - Number of cached polls should not exceed 10'.format(poller_id, poller))
                elif poll_len == 0:
                    errorlist.append('Error: Poller {} ID: {} - Pollers not running'.format(poller_id, poller))

        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reported.")

    def test_5_poller_current_data(self):
        msg = "Description: Display most current data from poller"
        if fit_common.VERBOSITY >= 2:
            print "\t{0}".format(msg)

        errorlist = []
        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                nodetype = get_rackhd_nodetype(node)
                print "\nNode: {} Type: {}".format(node, nodetype)
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                if fit_common.VERBOSITY >= 2:
                    print "Poller: {}  ID: {} ".format(poller, str(poller_id))
                monurl = "/api/2.0/pollers/" + str(poller_id) + "/data/current"
                mondata = fit_common.rackhdapi(url_cmd=monurl)
                if mondata['status'] not in [200, 201, 202, 204]:
                    errorlist.append("Error: Node {} Poller_ID {} Failed to get current poller data, status {}".format(node, poller_id, mondata['status']))
                else:
                    if fit_common.VERBOSITY >= 2:
                        print fit_common.json.dumps(mondata['json'], indent=4)

        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reported.")

    def test_6_poller_status_timestamp(self):
        msg = "Description: Display status and timestamp from current poll"
        if fit_common.VERBOSITY >= 2:
            print "\t{0}".format(msg)

        errorlist = []
        for node in NODELIST:
            nodetype = get_rackhd_nodetype(node)
            if fit_common.VERBOSITY >= 2:
                print "\nNode: {} Type: {}".format(node, nodetype)
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                if fit_common.VERBOSITY >= 2:
                    print "Poller: {}  ID: {} ".format(poller, str(poller_id))
                monurl = "/api/2.0/pollers/" + str(poller_id) + "/data/current"
                mondata = fit_common.rackhdapi(url_cmd=monurl)
                if mondata['status'] == 200:
                    if fit_common.VERBOSITY >= 2:
                        print "Timestamp: {}".format(mondata['json'][0]['timestamp'])
                else:
                    errorlist.append("Error: Node {} Poller_ID {} Failed to get current poller data, status {}".format(node, poller_id, mondata['status']))
        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reported.")

    def test_7_nodes_id_pollers(self):
        msg = "Description: Display the poller updated-at per node."
        if fit_common.VERBOSITY >= 2:
            print "\t{0}".format(msg)

        errorlist = []
        for node in NODELIST:
            if fit_common.VERBOSITY >= 2:
                nodetype = get_rackhd_nodetype(node)
                print "\nNode: {} Type: {}".format(node, nodetype)
            mondata = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertIn(mondata['status'], [200], "Incorrect HTTP return code, expecting 200, received {}".format(mondata['status']))
            for item in mondata['json']:
                # check required fields
                if item['pollInterval'] == 0:
                    errorlist.append("Node: {} pollInterval field error: {}".format(node, item['pollInterval']))
                for subitem in ['node', 'config', 'createdAt', 'id', 'name', 'config', 'updatedAt']:
                    if subitem not in item:
                        errorlist.append("Node: {} field error: {}".format(node, subitem))
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                poll_data = fit_common.rackhdapi("/api/2.0/pollers/" + poller_id)
                if fit_common.VERBOSITY >= 2:
                    print "Poller: {}  ID: {} ".format(poller, str(poller_id))
                    print "Created At: {}".format(fit_common.json.dumps(poll_data['json'].get('createdAt')))
                    print "Updated At: {}".format(fit_common.json.dumps(poll_data['json'].get('updatedAt')))
        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print "{}".format(fit_common.json.dumps(errorlist, indent=4))
            self.assertEqual(errorlist, [], "Error reporterd.")

if __name__ == '__main__':
    fit_common.unittest.main()
