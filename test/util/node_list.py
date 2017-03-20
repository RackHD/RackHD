'''
Copyright 2016, EMC, Inc

This utility lists the number and type of compute nodes in a stack.

Author(s):
George Paulos
'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import argparse
import fit_common


class test_list_nodes(fit_common.unittest.TestCase):
    def test_node_list(self):
        fit_common.VERBOSITY = 1
        print "\nNode List:"
        print "----------------------------------------------------------------------"
        skulist = fit_common.rackhdapi("/api/1.1/skus")['json']
        nodelist = fit_common.rackhdapi("/api/1.1/nodes")['json']
        for sku in skulist:
            nodecount = fit_common.json.dumps(nodelist).count(sku['id'])
            if nodecount > 0:
                print sku['name'] + ": " + str(nodecount)
            for node in nodelist:
                if 'sku' in node and  node['sku'] == sku['id']:
                    print "    " + node['id'] + " - Type: " + node['type']
        print "Unknown:"
        for node in nodelist:
                if 'sku' not in node:
                    print "    " + node['id'] + " - Type: " + node['type']
        print

if __name__ == '__main__':
    fit_common.unittest.main()

