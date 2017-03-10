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
@attr(api_1_1=True)
class rackhd11_api_nodes(fit_common.unittest.TestCase):
    def test_api_11_nodes(self):
        nodelist = []
        api_data = fit_common.rackhdapi('/api/1.1/nodes')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertGreater(len(api_data['json']), 0, 'nodes error')

        for nodeid in api_data['json']:
            if nodeid['type'] == 'compute':
                nodelist.append(nodeid)

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

    def test_api_11_nodes_ID(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid)
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            # check required fields
            for item in ['id', 'name', 'id', 'updatedAt', 'createdAt', 'type']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item
                self.assertGreater(len(api_data['json'][item]), 0, item + ' field error')

    def test_api_11_create_delete_node(self):
        data_payload = {"identifiers": ["00:1e:67:98:bc:7e"],
                        "profile": "diskboot.ipxe", "name": "test"}
        mon_url = "/api/1.1/nodes?identifiers=00:1e:67:98:bc:7e"
        api_data = fit_common.rackhdapi(mon_url, action='post', payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item
            self.assertGreater(len(item), 0, 'Empty JSON Field')
        api_data = fit_common.rackhdapi(mon_url)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/1.1/nodes/00:1e:67:98:bc:7e", action='delete')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/1.1/nodes/00:1e:67:98:bc:7e")
        self.assertEqual(api_data['status'], 404, 'Incorrect HTTP return code, expected 404, got:' + str(api_data['status']))

    def test_api_11_nodes_ID_pollers(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid + "/pollers")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for item in api_data['json']:
                # check required fields
                self.assertGreater(item['pollInterval'], 0, 'pollInterval field error')
                for subitem in ['node', 'config', 'createdAt', 'id', 'name']:
                    if fit_common.VERBOSITY >= 2:
                        print "Checking:", item['name'], subitem
                    self.assertIn(subitem, item, subitem + ' field error')

    def test_api_11_nodes_ID_workflows(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid + "/workflows")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for item in api_data['json']:
                # check required fields
                for subitem in ['createdAt', 'context', 'definition']:
                    if fit_common.VERBOSITY >= 2:
                        print "Checking:", item['name'], subitem
                    self.assertIn(subitem, item, subitem + ' field error')

    def test_api_11_nodes_ID_workflows_active(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid +  "/workflows/active")
            self.assertIn(api_data['status'], [204, 200], "Incorrect HTTP return code")
        # needs an active workflow to report
        # future work to create an active workflow then run report

    def test_api_11_nodes_ID_alias(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid + "?identifiers=alias")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            # check required fields
            for item in ['name', 'autoDiscover', 'updatedAt', 'createdAt', 'tags', 'type']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", api_data['json']['id'], item
                self.assertGreater(len(str(api_data['json'][item])), 0, item + ' field error')

    def test_api_11_nodes_ID_dhcp_whitelist(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            node_mac = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid)['json']["identifiers"][0]
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + node_mac +
                                               "/dhcp/whitelist", action='post')
            self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + node_mac +
                                               "/dhcp/whitelist", action='delete')
            self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))

    def test_api_11_nodes_ID_obmsettings(self):
        # create fake node
        data_payload = {'identifiers':['00:1e:67:aa:aa:aa'], 'name':'fakenode'}
        api_data = fit_common.rackhdapi("/api/1.1/nodes", action="post", payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        obm_id = api_data['json']['id']
        # assign OBM
        data_payload = {'obmSettings': [
            {'service': 'ipmi-obm-service',
             'config': {'user': 'root', 'password': '1234567',
                        'host': '172.31.128.100'}}]}
        mon_url = "/api/1.1/nodes/" + obm_id
        api_data = fit_common.rackhdapi(mon_url, action="patch", payload=data_payload)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # delete node
        api_data = fit_common.rackhdapi(mon_url, action="delete")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi(mon_url)
        self.assertEqual(api_data['status'], 404, 'Incorrect HTTP return code, expected 404, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
