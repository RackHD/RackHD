'''
Copyright 2017, Dell, Inc.

Author(s):
Davidjohn Blodgett

Readonly test script that tests:
-All the readonly service APIs
-Validation workflow(s) cannot be run against node in readonly mode.
'''

import fit_path  # NOQA: unused import
import unittest
import fit_common
import flogging
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


@attr(all=False, regression=False, smoke=False)
class rackhd_api_nodes_readonly(unittest.TestCase):
    def test_api_20_nodes_readonly(self):
        # TODO: will need to add a node to the list before checking for any...
        nodelist = []
        api_data = fit_common.rackhdapi('/api/2.0/nodes/readonly')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertGreater(len(api_data['json']), 0, 'no readonly nodes exist when expected')

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

    # DELETE
    # TODO: write test...


if __name__ == '__main__':
    unittest.main()
