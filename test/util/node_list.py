'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Purpose:
  This utility lists the number and type of compute nodes in a stack.
'''

import fit_path  # NOQA: unused import
import fit_common


class test_list_nodes(fit_common.unittest.TestCase):
    def test_node_list(self):
        fit_common.VERBOSITY = 1  # this is needed for suppressing debug messages to make reports readable
        print "\nNode List:"
        print "----------------------------------------------------------------------"
        skulist = fit_common.rackhdapi("/api/2.0/skus")['json']
        nodelist = fit_common.rackhdapi("/api/2.0/nodes")['json']
        for sku in skulist:
            nodecount = fit_common.json.dumps(nodelist).count(sku['id'])
            if nodecount > 0:
                print sku['name'] + ": " + str(nodecount)
            for node in nodelist:
                if 'sku' in node and str(sku['id']) in str(node['sku']):
                    print "    " + node['id'] + " - Type: " + node['type']
        print "Unknown:"
        for node in nodelist:
                if 'sku' not in node:
                    print "    " + node['id'] + " - Type: " + node['type']
        print


if __name__ == '__main__':
    fit_common.unittest.main()
