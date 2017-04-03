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


# Local methods
NODECATALOG = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_nodes(fit_common.unittest.TestCase):
    def test_api_20_nodes(self):
        nodelist = []
        api_data = fit_common.rackhdapi('/api/2.0/nodes')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertGreater(len(api_data['json']), 0, 'nodes error')

        for mon_node in api_data['json']:
            if mon_node['type'] != 'switch' and \
               mon_node['type'] != 'mgmt' and \
               mon_node['type'] != 'enclosure':
                nodelist.append(mon_node)

        # duplicate check
        for nodenum in range(1, len(nodelist)):
            # check node ID, name, identifiers(MACs)
            for nodecheck in range(0, len(nodelist)):
                if nodenum != nodecheck:
                    self.assertNotEqual(nodelist[nodenum]['id'], nodelist[nodecheck]['id'],
                                        "Duplicate node id " + nodelist[nodenum]['id'])
                    self.assertNotEqual(nodelist[nodenum]['name'], nodelist[nodecheck]['name'],
                                        "Duplicate node name " + nodelist[nodenum]['id'])
                    self.assertNotEqual(nodelist[nodenum]['identifiers'],
                                        nodelist[nodecheck]['identifiers'],
                                        "Duplicate node identifiers " + nodelist[nodenum]['id'])

    def test_api_20_nodes_ID(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid)
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            # check required fields
            for item in ['id', 'name', 'id', 'type']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item
                self.assertGreater(len(api_data['json'][item]), 0, item + ' field error')

    def test_api_20_create_delete_node(self):
        data_payload = {"name": "testnode", "identifiers": ["FF", "FF"], "type": "compute"}
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action='post', payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        nodeid = api_data['json']['id']
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item
            self.assertGreater(len(item), 0, 'Empty JSON Field')
        api_data = fit_common.rackhdapi("/api/2.0/nodes")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid, action='delete')
        self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid)
        self.assertEqual(api_data['status'], 404, 'Incorrect HTTP return code, expected 404, got:' + str(api_data['status']))

    def test_api_20_nodes_ID_pollers(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/pollers")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for item in api_data['json']:
                # check required fields
                self.assertGreater(item['pollInterval'], 0, 'pollInterval field error')
                for subitem in ['node', 'config', 'createdAt', 'id', 'name']:
                    if fit_common.VERBOSITY >= 2:
                        print "Checking:", item['name'], subitem
                    self.assertIn(subitem, item, subitem + ' field error')

    def test_api_20_nodes_ID_workflows(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/workflows")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for item in api_data['json']:
                # check required fields
                for subitem in ['createdAt', 'context', 'definition']:
                    if fit_common.VERBOSITY >= 2:
                        print "Checking:", item['name'], subitem
                    self.assertIn(subitem, item, subitem + ' field error')

    def test_api_20_nodes_ID_alias(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "?identifiers=alias")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            # check required fields
            for item in ['name', 'identifiers', 'type']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", api_data['json']['id'], item
                self.assertGreater(len(str(api_data['json'][item])), 0, item + ' field error')

    def test_api_20_nodes_ID_obmsettings(self):
        # create fake node
        data_payload = {"name": "testnode", "identifiers": ["FF", "FF"], "type": "compute"}
        api_data = fit_common.rackhdapi("/api/2.0/nodes", action="post",
                                           payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        obm_id = api_data['json']['id']
        # assign OBM
        data_payload = {'obmSettings': [
            {'service': 'ipmi-obm-service',
             'config': {'user': 'root', 'password': '1234567',
                        'host': '172.31.128.100'}}]}
        mon_url = "/api/2.0/nodes/" + obm_id
        api_data = fit_common.rackhdapi(mon_url, action="patch", payload=data_payload)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # delete node
        api_data = fit_common.rackhdapi(mon_url, action="delete")
        self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi(mon_url)
        self.assertEqual(api_data['status'], 404, 'Incorrect HTTP return code, expected 404, got:' + str(api_data['status']))

    def test_api_20_nodes_ID_ssh(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            payload = {"service": "ssh-ibm-service", "config": {"host": "1.1.1.1", "user": "user", "password": "1234567"}}
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/ssh", action="post", payload=payload)
            self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/ssh")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_api_20_nodes_readonly(self):
        @unittest.skipUnless("node_readonly" in fit_common.fitcfg(), "")
        # TODO: will need to add a node to the list before checking for any...
        nodelist = []
        api_data = fit_common.rackhdapi('/api/2.0/nodes/readonly')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertGreater(len(api_data['json']), 0, 'nodes error')

        for mon_node in api_data['json']:
            if mon_node['type'] != 'switch' and \
               mon_node['type'] != 'mgmt' and \
               mon_node['type'] != 'enclosure':
                nodelist.append(mon_node)

        # duplicate check
        for nodenum in range(1, len(nodelist)):
            # check node ID, name, identifiers(MACs)
            for nodecheck in range(0, len(nodelist)):
                if nodenum != nodecheck:
                    self.assertNotEqual(nodelist[nodenum]['id'], nodelist[nodecheck]['id'],
                                        "Duplicate node id " + nodelist[nodenum]['id'])
                    self.assertNotEqual(nodelist[nodenum]['name'], nodelist[nodecheck]['name'],
                                        "Duplicate node name " + nodelist[nodenum]['id'])
                    self.assertNotEqual(nodelist[nodenum]['identifiers'],
                                        nodelist[nodecheck]['identifiers'],
                                        "Duplicate node identifiers " + nodelist[nodenum]['id'])


if __name__ == '__main__':
    fit_common.unittest.main()
