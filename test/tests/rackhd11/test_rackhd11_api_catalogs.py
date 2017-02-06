'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
import fit_path
import fit_common
import flogging

logs = flogging.get_loggers()

# Local methods
MON_NODES = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd11_api_catalogs(fit_common.unittest.TestCase):
    def test_api_11_catalogs(self):
        api_data = fit_common.rackhdapi('/api/1.1/catalogs')
        self.assertEqual(api_data['status'], 200,
                        'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertNotEqual(len(api_data['json']), 0, "Error, no catalog")
        logs.debug_0('examining %d entries from catalogs', len(api_data['json']))
        for item in api_data['json']:
            # check required fields
            req_fields = ['createdAt', 'node', 'source', 'updatedAt', 'data']
            logs.debug_1('Checking catalog-id %s for required fields %s', item['id'], req_fields)
            for subitem in req_fields:
                logs.debug_2("Checking catalog-id %s for existance of required field '%s'", item['id'], subitem)
                self.assertIn(subitem, item, subitem + ' field error')

    def test_api_11_nodes_ID_catalogs(self):
        # iterate through nodes
        logs.debug_0('Going to check catalogs in nodes %s', MON_NODES)
        for nodeid in MON_NODES:
            api_data = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid + "/catalogs")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            logs.debug_1('examining %d catalogs from nodeid %s', len(api_data['json']), nodeid)
            for item in api_data['json']:
                self.assertNotEqual(item, '', 'Empty JSON Field')
                logs.debug_2("Checking source %s for nodeid %s", item['source'], nodeid)
                sourcedata = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid +
                                                     "/catalogs/" + item['source'])
                self.assertGreater(len(sourcedata['json']['id']), 0, 'id field error')
                self.assertGreater(len(sourcedata['json']['node']), 0, 'node field error')
                self.assertGreater(len(sourcedata['json']['source']), 0, 'source field error')
                self.assertGreater(len(sourcedata['json']['updatedAt']), 0, 'updatedAt field error')
                self.assertGreater(len(sourcedata['json']['createdAt']), 0, 'createdAt field error')

    def test_api_11_nodes_ID_catalogs_source(self):
        # iterate through sources
        api_data = fit_common.rackhdapi('/api/1.1/catalogs')
        for sourceid in api_data['json']:
            # iterate through nodes
            for nodeid in MON_NODES:
                api_data = fit_common.rackhdapi("/api/1.1/nodes/" + nodeid + "/catalogs/" + sourceid['source'])
                self.assertIn(api_data['status'], [200, 404], 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.run_from_module(__file__)
