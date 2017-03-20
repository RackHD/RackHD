'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Purpose:
   This is a utility to  display variuos node firmware and manufacturer info.
'''

import fit_path  # NOQA: unused import
import json
import pprint
import fit_common
import test_api_utils

# Globals

NODELIST = fit_common.node_select()
if NODELIST == []:
    print "No nodes found on stack"
    exit
fit_common.VERBOSITY = 1  # this is needed for suppressing debug messages to make reports readable


def mon_get_ip_info(node):
    '''
    This routine will grab the IP information from the compute node
    '''
    # Get RackHD node info
    nodeurl = "/api/2.0/nodes/" + node
    nodedata = fit_common.rackhdapi(nodeurl, action="get")
    nodeinfo = nodedata['json']
    result = nodedata['status']
    if result != 200:
        print "Error on node command ", nodeurl
        fit_common.TEST_CASE["test_error"] += 1
        return

    # get RackHD BMC info
    monurl = "/api/2.0/nodes/" + node + "/catalogs/bmc"
    mondata = fit_common.rackhdapi(monurl, action="get")
    catalog = mondata['json']
    result = mondata['status']
    if result != 200:
        print "Error on catalog/bmc command ", monurl
    else:
        print " BMC MAC Address: " + catalog["data"]["MAC Address"]
        bmc_ip_value = catalog["data"].get("IP Address")
        print " Shared NIC BMC IP Address: " + bmc_ip_value
        print " Shared NIC BMC IP Address Source: " + catalog["data"]["IP Address Source"]

        # Check BMC IP vs OBM IP setting
        try:
            obmlist = nodeinfo["obmSettings"]
        except:
            print "ERROR: Node has no OBM settings configured"
        else:
            if fit_common.VERBOSITY >= 3:
                print " OBM Settings:"
                print fit_common.json.dumps(obmlist, indent=4)
            try:
                obmlist[0]["config"]["host"]
            except:
                print "ERROR: Invalid or empty OBM setting"

    # Get RackHD RMM info
    monurl = "/api/2.0/nodes/" + node + "/catalogs/rmm"
    mondata = fit_common.rackhdapi(monurl, action="get")
    catalog = mondata['json']
    result = mondata['status']
    if result != 200:
        print "\nNo RMM catalog for node"
    else:
        print " RMM MAC Address: " + catalog["data"].get("MAC Address")
        print " RMM IP Address: " + catalog["data"].get("IP Address")
        print " RMM IP Address Source: " + catalog["data"].get("IP Address Source")


def redfish_simple_storage_members(node_id):
    """
    To get the device ids from simple storage for a given node_id
    :param nodeid:   node id
    """

    on_url = "/redfish/v1/Systems/" + str(node_id) + '/SimpleStorage'
    on_data = fit_common.rackhdapi(url_cmd=on_url)

    # To get a list of devices
    dev_ids = []
    try:
        members = on_data['json']["Members"]
    except KeyError:
        members = []

    for member in members:
        href_id = member["@odata.id"]
        dev_id = href_id.split('/')[-1]
        dev_ids.append(dev_id)

    return dev_ids


class display_node_firmware(fit_common.unittest.TestCase):
    # This test displays the BMC and BIOS firmware versions from the
    # RackHD catalog data and the onrack redfish calls
    # No asserts are used in this test, avoiding early exit on errors
    def test_display_bmc_bios(self):
        ora_name = ""
        inode = 1
        for node in NODELIST:
            print "==== Displaying BMC BIOS ===="
            # Print the SKU info from onrack
            print "\nNode " + str(inode) + ": " + node
            print "Redfish SKU data:"
            # Redfish 1.0
            on_url = "/redfish/v1/Systems/" + node
            on_data = fit_common.rackhdapi(url_cmd=on_url)
            if on_data['status'] == 200:
                sysdata = on_data['json']
                ora_name = sysdata.get("Name", "")
                print "Name: ", ora_name
                print "AssetTag: ", sysdata.get("AssetTag", "")
                print "SKU: ", sysdata.get("SKU", "")
                print "BiosVersion: ", sysdata.get("BiosVersion", "")
                print "PowerState: ", sysdata.get("PowerState", "")
                print "SerialNumber: ", sysdata.get("SerialNumber", "")
                print " Model: ", sysdata.get("Model", "")
            else:
                print "Status: ", on_data['status']

            # Print the related system info from RackHD
            print "\nRackHD System Info from DMI:"
            monurl = "/api/2.0/nodes/" + node + "/catalogs/dmi"
            mondata = fit_common.rackhdapi(monurl, action="get")
            catalog = mondata['json']
            result = mondata['status']
            # increment the error counter, but don't exit with an assert if no DMI catalog
            if result != 200:
                print "Error on catalog/dmi command"
            else:
                print " ID: " + catalog["id"]
                print " Product Name : ", catalog["data"]["System Information"].get("Product Name", "")
                print " Serial Number: ", catalog["data"]["System Information"].get("Serial Number", "")
                print " UUID         : ", catalog["data"]["System Information"].get("UUID", "")
                print " BMC FW Revision : ", catalog["data"]["BIOS Information"].get("Firmware Revision", "")
                print " Release Date    : ", catalog["data"]["BIOS Information"].get("Release Date", "")
                print " BIOS FW Package : ", catalog["data"]["BIOS Information"].get("Version", "")
                print " BIOS Vendor     : ", catalog["data"]["BIOS Information"].get("Vendor", "")
            print "ORA Name      : ", ora_name
            print "\nIP Info:"
            mon_get_ip_info(node)
            inode += 1
        print "=========================================================\n"

    def test_display_bmc_mc_info(self):
        # This test displays the BMC MC info from the compute node via
        # IPMI call ipmitool mc info
        # No asserts are used in this test, avoiding early exit on errors
        inode = 1
        for node in NODELIST:
            print "==== Displaying BMC MC info ===="
            nodetype = test_api_utils.get_rackhd_nodetype(node)
            print "\nNode " + str(inode) + ": " + node
            print "Type: ", nodetype
            if nodetype != "unknown" and nodetype != "Unmanaged":
                nodeurl = "/api/2.0/nodes/" + node
                nodedata = fit_common.rackhdapi(nodeurl, action="get")
                nodeinfo = nodedata['json']
                result = nodedata['status']
                if result != 200:
                    print "Error on node command" + nodeurl
                else:
                    try:
                        obmlist = nodeinfo["obmSettings"]
                    except:
                        print "ERROR: Node has no OBM settings configured"
                    else:
                        if obmlist:
                            bmc_ip = test_api_utils.get_compute_bmc_ip(node)
                            if bmc_ip in [1, 2]:
                                print "No BMC IP found"
                            elif bmc_ip.startswith('192.168'):
                                print "ERROR: BAD BMC Value: ", bmc_ip
                            else:
                                user_cred = test_api_utils.get_compute_node_username(node)
                                if user_cred in [1, 2, 3, 4]:
                                    print "Unable to get user credetials for node_id", node
                                else:
                                    mc_data = test_api_utils.run_ipmi_command(bmc_ip, 'mc info', user_cred)
                                    if mc_data['exitcode'] == 0:
                                        print "MC Data: "
                                        print mc_data['stdout']
                        else:
                            print "ERROR: Node has no OBM settings configured"
                inode += 1
        print "=========================================================\n"

    def test_display_raid_controller_firmware(self):
        # This test displays the MegaRaid controller firmware data from the compute
        # node if it exists.  It then displays the controller info contained in the
        # RackHD redfish managed system data
        # No asserts are used in this test, avoiding early exit on errors
        inode = 1
        for node in NODELIST:
            print "==== Displaying MegaRAID and Controller info ===="
            source_set = []
            nodetype = test_api_utils.get_rackhd_nodetype(node)
            print "\nNode " + str(inode) + ": " + node
            print "Type: ", nodetype
            if nodetype != "unknown" and nodetype != "Unmanaged":
                monurl = "/api/2.0/nodes/" + node + "/catalogs"
                mondata = fit_common.rackhdapi(monurl, action="get")
                catalog = mondata['json']
                result = mondata['status']
                if result != 200:
                    print "ERROR: failed catalog request"
                else:
                    source_set = test_api_utils.get_node_source_id_list(node)
                    if 'megaraid-controllers' in source_set:
                        print "Source: megaraid-controllers\n"
                        raidurl = "/api/2.0/nodes/" + node + "/catalogs/megaraid-controllers"
                        raiddata = fit_common.rackhdapi(raidurl, action="get")
                        catalog = raiddata['json']
                        result = raiddata['status']
                        print " Basics: ", catalog["data"]["Controllers"][0]["Command Status"]
                        print " Version: ",
                        pprint.pprint(catalog["data"]["Controllers"][0]["Response Data"]["Version"])
                    else:
                        print "Info: monorail catalog did not contain megraid-controllers source"
                    # display controller data if available, no firmware revs are present in the output
                    device_ids = redfish_simple_storage_members(node)
                    for dev_id in device_ids:
                        devurl = "/redfish/v1/Systems/" + node + "/SimpleStorage/" + dev_id
                        devdata = fit_common.rackhdapi(url_cmd=devurl)
                        controller = devdata['json']
                        result = devdata['status']
                        if result == 200:
                            controller = devdata['json']
                            print "Controller: " + str(dev_id) + " Name: " + str(controller.get('Name', ""))
                            print "Description: ", json.dumps(controller.get('Description', ""), indent=4)
            inode += 1
        print "========================================================="


if __name__ == '__main__':
    fit_common.unittest.main()
