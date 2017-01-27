"""
Copyright 2017, EMC, Inc.
"""
import sys
import subprocess
import unittest
import flogging
from on_http_api2_0 import ApiApi as Api
# TODO remove when 2.0 worklfow API is implemented
from config.api1_1_config import config as config_old
from config.api2_0_config import config
from json import loads
from common.api_utils import api_node_select_from_config, api_node_select, api_validate_node_pollers
from nose.plugins.attrib import attr

# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test")
logs = flogging.get_loggers()


@attr(all=True, regression=True, smoke=True)
class NodesTests(unittest.TestCase):
    def setUp(self):
        self.__client_old = config_old.api_client
        self.__client = config.api_client

    def shortDescription(self):
        # This removes the doctrings (""") from test list (collect-only)
        return None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def test_type_list(self):
        """validates test utility method api_node_select() using an obm mac address will return the correct node id"""

        type_list = ['compute', 'switch', 'enclosure', 'pdu', 'foo']

        Api().nodes_get_all()
        node_list = self.__get_data()
        type_count = 0

        for type_entry in type_list:
            logs.debug('Testing node type %s', type_entry)
            for node in node_list:
                if node.get('type') == type_entry:
                    type_count += 1

            id_list = api_node_select(self.__client, node_type=type_entry)
            self.assertNotEqual(len(node_list),
                                type_count,
                                msg='For node type {}: id list cnt {} != node type list len({})'.format(type_entry,
                                                                                                        type_count,
                                                                                                        len(id_list)))
            type_count = 0

    def test_node_id_list(self):
        """validates test utility method api_node_select() detects if a provided node id is valid"""

        Api().nodes_get_all()
        node_list = self.__get_data()

        for node in node_list:
            self.assertNotEqual(0,
                                api_node_select(self.__client, node_id=node.get('id')),
                                msg='Node id {} not found in Id list'.format(node.get('id')))

    def test_skuName(self):
        """Validates test utility method api_node_select() outputs all nodes for a provided sku name"""

        Api().nodes_get_all()
        node_list = self.__get_data()
        for node in node_list:
            if 'sku' in node and node.get('sku'):
                Api().skus_id_get(identifier=node.get('sku').split('/')[-1])
                sku = self.__get_data()

                sku_name = sku.get('name')
                if sku_name:
                    id_list = api_node_select(self.__client, sku_name=sku_name)
                    self.assertIn(node['id'], id_list, msg='Node id {} not found in Id list'.format(node.get('id')))

    def test_bad_skuName(self):
        """validates test utility method api_node_select() detects invalid sku type"""

        id_list = api_node_select(self.__client, sku_name='foo')

        self.assertEqual(0, len(id_list), msg='Invalid sku id of "foo" detected')

    def test_all_node_obm_validation(self):
        """validates test utility method api_node_select() outputs nodes with validate obm settings"""

        Api().nodes_get_all()
        node_list = self.__get_data()

        node_count = 0
        for node in node_list:
            if node.get('type') == 'compute':
                if 'obms' in node and len(node['obms']) > 0:
                    node_count += 1

        id_list = api_node_select(self.__client, validate_obm=True)
        self.assertEqual(node_count,
                         len(id_list),
                         msg='Not all nodes have OBM settings {}:{}'.format(node_count, len(id_list)))

    def test_node_obm_validation(self):
        """validates test utility method api_node_select() using node id will validate node obm settings"""

        Api().nodes_get_all()
        node_list = self.__get_data()

        for node in node_list:
            if node.get('type') == 'compute':
                if 'obms' in node and len(node['obms']) > 0:
                    id_list = api_node_select(self.__client, node_id=node['id'], validate_obm=True)
                    self.assertIn(node['id'], id_list, msg='Node {} OBM settings not detected'.format(node['id']))

    def test_obmMac(self):
        """validates test utility method api_node_select() using obm mac address will return the correct node id"""

        obm_count = 0
        Api().nodes_get_all()
        node_list = self.__get_data()

        for node in node_list:
            if 'sku' in node:
                Api().nodes_get_obms_by_node_id(identifier=node.get('id'))
                obm_list = self.__get_data()
                for obm_entry in obm_list:
                    if obm_entry['config']:
                        obm_mac = obm_entry['config'].get('host')
                        id_list = api_node_select(self.__client, obm_mac=obm_mac)
                        self.assertEqual(1,
                                         len(id_list),
                                         msg='Expected a list size of 1 got {} - node id {}'.format(len(id_list),
                                                                                                    node['id']))
                        self.assertIn(node['id'],
                                      id_list,
                                      msg='Node id {} with obm mac ({}) not found in Id list'.format(node.get('id'),
                                                                                                     obm_mac))
                        obm_count += 1
        self.assertGreater(obm_count, 0, msg='No nodes with OBM found')

    def test_all_list_arg_node_type(self):
        """validates test utility method api_node_select_from_config() using obm mac address will return the correct node id"""

        type_list = ['compute', 'switch', 'enclosure', 'pdu', 'foo']

        Api().nodes_get_all()
        node_list = self.__get_data()
        type_count = 0

        for type_entry in type_list:
            logs.debug('Testing node type %s', type_entry)
            for node in node_list:
                if node.get('type') == type_entry:
                    type_count += 1

            id_list = api_node_select_from_config(node_type=type_entry)
            self.assertEqual(len(id_list),
                             type_count,
                             msg='For node type {}: id list cnt {} != node type list len({})'.format(type_entry,
                                                                                                     type_count,
                                                                                                     len(id_list)))
            type_count = 0

    def test_all_list_arg_node_validate(self):
        """validates test utility method api_node_select_from_config() will return the correct nodes with valid obm settings"""

        Api().nodes_get_all()
        node_list = self.__get_data()

        node_count = 0
        for node in node_list:
            if node.get('type') == 'compute':
                if 'obms' in node and len(node['obms']) > 0:
                    node_count += 1

        id_list = api_node_select_from_config(validate_obm=True)
        self.assertEqual(node_count,
                         len(id_list),
                         msg='Not all nodes have OBM settings {}:{}'.format(node_count, len(id_list)))

    def test_poller_one(self):
        """validates test utility method api_validate_node_pollers() will return nodes with one active poller"""

        valid_compute_nodes = api_node_select(self.__client, validate_obm=True)
        polled_response = api_validate_node_pollers(self.__client, valid_compute_nodes)
        self.assertTrue(polled_response, msg='Not all pollers active')

    def test_poller_all(self):
        """validates test utility method api_validate_node_pollers() will return nodes with all active pollers"""

        valid_compute_nodes = api_node_select(self.__client, validate_obm=True)
        polled_response = api_validate_node_pollers(self.__client, valid_compute_nodes, all_pollers=True)
        self.assertTrue(polled_response, msg='Not all pollers active')

    def test_poller_bad_node(self):
        """validates test utility method api_validate_node_pollers() will detect pollers for invalid node"""

        polled_response = api_validate_node_pollers(self.__client, ['foo'], all_pollers=True)
        self.assertFalse(polled_response, msg='Got True for bad poller (foo)')
