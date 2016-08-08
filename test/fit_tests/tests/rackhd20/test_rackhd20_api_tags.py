'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common

# Local methods
MON_NODES = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_tags(fit_common.unittest.TestCase):
    def test_api_20_nodes_ID_tags(self):
        # iterate through nodes
        for nodeid in MON_NODES:
            #add tag
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/tags", action="patch", payload={"tags":["test_tag_" + nodeid]})
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            #check tag
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/tags")
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            self.assertIn("test_tag_" + nodeid, fit_common.json.dumps(api_data['json']), "Tag not set:" + fit_common.json.dumps(api_data['json']))
    def test_api_20_tags_post_delete(self):
        # create dummy node
        data_payload = {"identifiers": ["00:1e:67:98:bc:7f"],
                        "profile": "diskboot.ipxe", "name": "test"}
        mon_url = "/api/2.0/nodes?identifiers=00:1e:67:98:bc:7f"
        nodeid = fit_common.rackhdapi(mon_url, action='post', payload=data_payload)['json']['id']
        # add tags
        api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid + "/tags", action="patch", payload={"tags":["test_node","dummy_node"]})
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        # check tags
        api_data = fit_common.rackhdapi("/api/2.0/tags/test_node/nodes")
        self.assertIn("test_node", fit_common.json.dumps(api_data['json']), "Tag not set:" + fit_common.json.dumps(api_data['json']))
        self.assertIn("dummy_node", fit_common.json.dumps(api_data['json']), "Tag not set:" + fit_common.json.dumps(api_data['json']))
        # delete node
        api_data = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid, action="delete")
        self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
