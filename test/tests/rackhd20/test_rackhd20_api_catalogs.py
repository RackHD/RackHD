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
class rackhd20_api_catalogs(fit_common.unittest.TestCase):
    def test_api_20_catalogs(self):
        api_data = fit_common.rackhdapi('/api/2.0/catalogs')
        self.assertEqual(api_data['status'], 200,
                        'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertNotEqual(len(api_data['json']), 0, "Error, no catalog")
        for item in api_data['json']:
            # check required fields
            for subitem in ['node', 'id', 'source', 'data']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['id'], subitem
                self.assertIn(subitem, item, subitem + ' field error')

    def test_api_20_nodes_ID_catalogs(self):
        # iterate through nodes
        for nodeid in NODECATALOG:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/catalogs")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            for item in api_data['json']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking source:", item['source']
                self.assertNotEqual(item, '', 'Empty JSON Field')
                sourcedata = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid +
                                                     "/catalogs/" + item['source'])
                self.assertGreater(len(sourcedata['json']['id']), 0, 'id field error')
                self.assertGreater(len(sourcedata['json']['node']), 0, 'node field error')
                self.assertGreater(len(sourcedata['json']['source']), 0, 'source field error')
                self.assertGreater(len(sourcedata['json']['updatedAt']), 0, 'updatedAt field error')
                self.assertGreater(len(sourcedata['json']['createdAt']), 0, 'createdAt field error')

    def test_api_20_nodes_ID_catalogs_source(self):
        # iterate through sources
        api_data = fit_common.rackhdapi('/api/2.0/catalogs')
        for sourceid in api_data['json']:
            # iterate through nodes
            for nodeid in NODECATALOG:
                api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/catalogs/" + sourceid['source'])
                self.assertIn(api_data['status'], [200, 404], 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
