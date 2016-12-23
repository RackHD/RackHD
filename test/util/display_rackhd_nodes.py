# Copyright 2016, EMC, Inc.

"""
  Purpose:
  This script will generate a list of discovered nodes and identifiers
  using the RackHD API calls.
"""

#pylint: disable=relative-import

import os
import sys
import subprocess
import json
import pprint
from nosedep import depends

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common
import test_api_utils

class display_rackhd_node_list(fit_common.unittest.TestCase):
    def test_display_node_list(self):
        # This test displays a list of the nodes, type and name
        mondata = fit_common.rackhdapi("/api/1.1/nodes")
        nodes = mondata['json']
        result = mondata['status']
        if result == 200:
            # display nodes
            print '\n{:4s} {:26s} {:15s} {:132s}'.format(" ", "NodeId", "Node Type", "Node Name")
            i = 0
            if not nodes:
                print "No Nodes found on ORA server "
            else:
                for node in nodes:
                    i += 1
                    print '{:4s} {:26s} {:15s} {:132s}'.format(str(i), node['id'], node['type'], node['name'])
        else:
            print "Cannot get RackHD nodes from stack, http response code: ", result

    @depends(after='test_display_node_list')
    def test_display_node_list_discovery_data(self):
        # This test displays a list of the nodes along with 
        # the associated BMC, RMM, and OBM settings for the discovered compute nodes 
        mondata = fit_common.rackhdapi("/api/1.1/nodes")
        nodes = mondata['json']
        result = mondata['status']

        if result == 200:
            #print "result" + str(result)
            # Display node info
            print "\nNumber of nodes found: "+str(len(nodes))+"\n"
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
                    monurl = "/api/1.1/nodes/"+nn+"/catalogs/bmc"
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
                    rmmurl = "/api/1.1/nodes/"+nn+"/catalogs/rmm"
                    rmmdata = fit_common.rackhdapi(rmmurl, action="get")
                    rmmcatalog = rmmdata['json']
                    rmmresult = rmmdata['status']
                    if rmmresult != 200:
                        print "\tNo RMM catalog entry.\t\t\t\t\t",
                    else:
                        print "\t" + rmmcatalog["data"].get("MAC Address", "-"),
                        print "\t" + rmmcatalog["data"].get("IP Address", "-"),
                        print "\t" + rmmcatalog["data"].get("IP Address Source", "-") + "\t",

                    nodeurl = "/api/1.1/nodes/"+nn
                    nodedata = fit_common.rackhdapi(nodeurl, action="get")
                    nodeinfo = nodedata['json']
                    result = nodedata['status']
                    if result != 200:
                        print "Error on node command" + nodeurl + ", http response:  " + result
                    else:
                        # Check BMC IP vs OBM IP setting
                        try:
                            obmlist = nodeinfo["obmSettings"]
                        except:
                            print "ERROR: Node has no OBM settings configured"
                        else:
                            try:
                                obmhost = obmlist[0]["config"]["host"]
                            except:
                                print "Invalid or empty OBM setting"
                            else:
                                print obmhost,
                                print "\t" + obmlist[0]["config"].get("user","Error: No User defined!")
        else:
            print "Cannot get RackHD nodes from stack, http response code: ", result

if __name__ == '__main__':
    fit_common.unittest.main()
