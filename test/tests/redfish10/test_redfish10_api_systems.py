'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import fit_common
import flogging
log = flogging.get_loggers()


# Local methods
NODECATALOG = fit_common.node_select()

def _delete_active_tasks(node):
    for dummy in range(1,10):
        if fit_common.rackhdapi('/api/current/nodes/' + node + '/workflows/active', action='delete')['status'] in [204, 404]:
             return True
        else:
            fit_common.time.sleep(10)
    return False

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class redfish10_api_systems(fit_common.unittest.TestCase):
    def test_redfish_v1_systems(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Systems')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # check all fields
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print ("Checking: {0}".format(item))
            self.assertNotEqual(item, "", 'Empty JSON Field')

        # check required fields
        for item in ['Name', '@odata.id', '@odata.type']:
            if fit_common.VERBOSITY >= 2:
                print ("Checking: {0}".format(item))
            self.assertIn(item, api_data['json'], item + ' field not present')
            if fit_common.VERBOSITY >= 3:
                print ("\t {0}".format( api_data['json'][item]))
            self.assertGreater(len(api_data['json'][item]), 0, item + ' field empty')

        # test all nodeid links
        for item in api_data['json']['Members']:
            link_data = fit_common.rackhdapi(item['@odata.id'])
            # all these are legit return codes under different conditions
            self.assertEqual(link_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(link_data['status']))

    def test_redfish_v1_systems_id(self):
        api_data = fit_common.rackhdapi('/redfish/v1/Systems')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for nodeid in api_data['json']['Members']:
            api_data = fit_common.rackhdapi(nodeid['@odata.id'])
            if api_data['status'] == 200:  # if valid cache record, run chassis ID query
                # check required fields
                # check Name field first because that will be used for other checks
                self.assertIn('Name', api_data['json'], 'Name field not present')
                self.assertGreater(len(api_data['json']['Name']), 0, 'Name field empty')
                system_name = api_data['json']['Name']
                if fit_common.VERBOSITY >= 2:
                    print ("System Name: {0}".format(system_name))
                for item in ['SKU', 'BiosVersion', 'PowerState', 'Processors', '@odata.id', 'Status', 'UUID',
                             'Manufacturer', 'IndicatorLED']:
                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(item))
                        print ("\t {0}".format(api_data['json'][item]))
                    self.assertIn(item, api_data['json'], item + ' field not present')
                    # comment the following out until ODR-526 resolved, Unknown sytems return 
                    # a Name value of 'Computer System' instead of 'Unknown'
                    #if system_name != 'Unknown':
                    #    self.assertGreater(len(api_data['json'][item]), 0, item + ' field empty')

    def test_redfish_v1_systems_id_actions_computersystemreset_get(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/Actions/ComputerSystem.Reset')
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            reset_commands = [
                                "On",
                                "ForceOff",
                                "GracefulShutdown",
                                "GracefulRestart",
                                "ForceRestart",
                                "Nmi",
                                "ForceOn",
                                "PushPowerButton"
                              ]
            # iterate through all posted reset types for each node
            for reset_type in api_data['json']['reset_type@Redfish.AllowableValues']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking: {0}".format(reset_type)
                self.assertIn(reset_type, reset_commands, "Incorrect reset_type")

    def test_redfish_v1_systems_id_actions_computersystemreset_post(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            # delete previously active tasks
            _delete_active_tasks(nodeid)
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/Actions/ComputerSystem.Reset')
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            on_payload = {"reset_type": "On"}
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid +
                                            '/Actions/ComputerSystem.Reset', action='post',
                                            payload=on_payload)
            self.assertEqual(api_data['status'], 202, 'Incorrect HTTP return code, expected 202, got:' + str(api_data['status']))
            # check for running task
            task_data = fit_common.rackhdapi(api_data['json']['@odata.id'])
            self.assertEqual(task_data['status'], 200, "No task ID for reset ")
            self.assertIn(task_data['json']['TaskState'], ["Running", "Pending", "Completed", "Exception"], "Bad task state for node:" + nodeid)

    def test_redfish_v1_systems_id_actions_rackhdbootimage_get(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/Actions/RackHD.BootImage')
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_redfish_v1_systems_id_logservices(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid)
            if api_data['status'] == 200:
                api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/LogServices')
                self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_redfish_v1_systems_id_processors_id(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/Processors')
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for links in api_data['json']['Members']:
                api_data = fit_common.rackhdapi(links['@odata.id'])
                self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
                for item in api_data['json']:
                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(item))
                        print ("\t {0}".format(api_data['json'][item]))
                    self.assertNotEqual(item, "", 'Empty JSON Field')

    def test_redfish_v1_systems_id_ethernetinterfaces(self):
        # Will produce a list of available Ethernet interfaces
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/EthernetInterfaces')
            self.assertIn(api_data['status'], [200], 'Expected 200, got:' + str(api_data['status']))

    def test_redfish_v1_systems_id_bios(self):
        # Only works for Dell servers with microservices
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/Bios')
            if fit_common.is_dell_node(nodeid):
                self.assertIn(api_data['status'], [200], 'Expected 200, got:' + str(api_data['status']))
            else:
                self.assertIn(api_data['status'], [404], 'Expected 404, got:' + str(api_data['status']))

    def test_redfish_v1_systems_id_bios_settings(self):
        # Only works for Dell servers with microservices
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/Bios/Settings')
            if fit_common.is_dell_node(nodeid):
                self.assertIn(api_data['status'], [200], 'Expected 200, got:' + str(api_data['status']))
            else:
                self.assertIn(api_data['status'], [404], 'Expected 404, got:' + str(api_data['status']))

    def test_redfish_v1_systems_id_simplestorage(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/SimpleStorage')
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_redfish_v1_systems_id_simplestorage_id(self):
        href_list = []
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/SimpleStorage')
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for nodeid in api_data['json']['Members']:
                href_list.append(nodeid['@odata.id']) # collect links
                self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # iterate through links
        for url in href_list:
            api_data = fit_common.rackhdapi(url)
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_redfish_v1_systems_id_logservices_sel(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/redfish/v1/Systems/" + nodeid + "/LogServices/SEL")
            if fit_common.VERBOSITY >= 2:
                print ("nodeid: {0}".format(nodeid))
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for item in ['MaxNumberOfRecords', 'OverWritePolicy', 'DateTimeLocalOffset', 'Actions']:
                if fit_common.VERBOSITY >= 2:
                    print ("Checking: {0}".format(item))
                    print ("\t {0}".format(api_data['json'][item]))
                self.assertIn(item, api_data['json'], item + ' field not present')
                self.assertGreater(len(str(api_data['json'][item])), 0, item + ' field empty')

    def test_redfish_v1_systems_id_logservices_sel_entries(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/redfish/v1/Systems/" + nodeid + "/LogServices/SEL/Entries")
            if fit_common.VERBOSITY >= 2:
                print ("nodeid: {0}".format(nodeid))
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

            # check required fields in the nodeid entry
            for nodeid in api_data['json']['Members']:
                self.assertIn('@odata.id', nodeid, '@odata.id field not present')
                self.assertGreater(len(nodeid['@odata.id']), 0, '@odata.id field empty')
                if fit_common.VERBOSITY >= 2:
                    print ("\nEntry {0}".format(nodeid['@odata.id']))
                for item in [ 'Id', 'Created', 'EntryCode', 'EntryType', 'SensorType', 'Name', 'Message' ]:
                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(item))
                    self.assertIn(item, nodeid, item + ' field not present')
                    if fit_common.VERBOSITY >= 3:
                        print ("\t {0}".format(nodeid[item]))
                    if len(nodeid[item]) == 0 and item == 'Message':
                        log.info_5("Message field empty for SEL SensorType:" + nodeid['SensorType'] +
                                   " SensorNumber:" + str(nodeid['SensorNumber']))
                    else:
                        self.assertGreater(len(nodeid[item]), 0, item + ' field empty')
                for link in [ 'OriginOfCondition' ]:

                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(link))
                    self.assertIn('OriginOfCondition', nodeid['Links'], 'OriginOfCondition' + ' field not present')
                    if fit_common.VERBOSITY >= 3:
                        print ("\t {0} ".format(nodeid['Links']['OriginOfCondition']))

    def test_redfish_v1_systems_id_logservices_sel_entries_id(self):
        # iterate through node IDs
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/redfish/v1/Systems/" + nodeid + "/LogServices/SEL/Entries")
            if fit_common.VERBOSITY >= 2:
                print ("nodeid: {0}".format(nodeid))
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

            for member in api_data['json']['Members']:
                self.assertIn('@odata.id', member, '@odata.id field not present')
                self.assertGreater(len(member['@odata.id']), 0, '@odata.id field empty')
                if fit_common.VERBOSITY >= 2:
                    print ("\nEntry {0}".format(member['@odata.id']))

                #get the selid off the list
                selid = str(member['Id'])
                if fit_common.VERBOSITY >= 3:
                    print ("SEL Entry: {0}".format(selid))

                #retrieve the data for the specific SEL entry and iterate through individual fields
                seldata = fit_common.rackhdapi("/redfish/v1/Systems/" + nodeid + "/LogServices/SEL/Entries/" + selid)
                self.assertEqual(seldata['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(seldata['status']))

                for item in [ 'Id', 'Created', 'EntryCode', 'EntryType', 'SensorType', 'Name', 'Message' ]:
                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(item))
                    self.assertIn(item, seldata['json'], item + ' field not present')
                    if fit_common.VERBOSITY >= 3:
                        print ("\t {0}".format(seldata['json'][item]))
                    if len(seldata['json'][item]) == 0 and item == 'Message':
                        log.info_5("Message field empty for SEL SensorType:" + seldata['json']['SensorType'] +
                                   " SensorNumber:" + str(seldata['json']['SensorNumber']))
                    else:
                        self.assertGreater(len(seldata['json'][item]), 0, item + ' field empty')

                for link in [ 'OriginOfCondition' ]:
                    if fit_common.VERBOSITY >= 2:
                        print ("Checking: {0}".format(link))
                    self.assertIn('OriginOfCondition', seldata['json']['Links'], 'OriginOfCondition' + ' field not present')
                    if fit_common.VERBOSITY >= 3:
                        print ("\t {0}".format(seldata['json']['Links']['OriginOfCondition']))

    def test_redfish_v1_systems_id_secureboot(self):
        # Currently relies on Dell/Racadm, so just test for exceptions
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/SecureBoot')
            self.assertEqual(api_data['status'], 500, 'Incorrect HTTP return code, expected 500, got:' + str(api_data['status']))
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/SecureBoot', action='post',
                                            payload={"zzzSecureBootEnable": True})
            self.assertEqual(api_data['status'], 400, 'Incorrect HTTP return code, expected 400, got:' + str(api_data['status']))
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid + '/SecureBoot', action='post',
                                            payload={"SecureBootEnable": True})
            self.assertEqual(api_data['status'], 500, 'Incorrect HTTP return code, expected 500, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
