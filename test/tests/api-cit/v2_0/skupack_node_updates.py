"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This test will delete all existing skus from the DUT and apply fake skus.
The skus then will be modified to verify that nodes will automatically update
their sku to the new matching sku.
"""
import fit_path  # NOQA: unused import
import fit_common
import time
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr
from api_utils import get_by_string

logs = flogging.get_loggers()

SKU_ATTACH_WAIT_TIME = 10


@attr(regression=False, smoke=True, skus_api2_tests=True)
class SkusTests(fit_common.unittest.TestCase):

    def setUp(self):
        self.__client = config.api_client

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def test_skus(self):
        # """Testing GET:api/2.0/skus to get list of skus"""
        Api().skus_get()
        rsp = self.__client.last_response
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        # todo: this used to load data that was not used so what does this do?
        loads(self.__client.last_response.data)

    @depends(after='test_skus')
    def test_delete_skus(self):
        # """Test DELETE:api/2.0/skus/:identifier"""
        logs.info(' Deleting possible sku mytestsku')
        Api().skus_get()
        rsp = self.__client.last_response
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        skus = loads(self.__client.last_response.data)

        for sku in skus:
            if sku.get("name") == "mytestsku":
                sku_id = sku.get('id')
                self.assertIsNotNone(sku_id, msg="mytestsku has id of None")
                logs.info('mytestsku found and deleting that sku')
                Api().skus_id_delete(identifier=sku_id)
                rsp = self.__client.last_response
                self.assertEqual(204, rsp.status, msg=rsp.reason)
                # Check is sku was deleted
                try:
                    Api().skus_id_get(identifier=sku_id)
                except ApiException as e:
                    self.assertEqual(404, e.status, msg='Expected 404, received {}'.format(e.status))

    @depends(after='test_delete_skus')
    def test_get_sku_nodes(self):
        # """Test GET /api/2.0/skus/:identifier/nodes"""
        mock_sku = {
            "name": "mytestsku",
            "rules": [
                {
                    "path": "dmi.Base Board Information.Serial Number",
                    "contains": " "
                }
            ]
        }

        # get current node list
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)

        # find node with sku attached
        node_id, original_sku_id = self.find_node_with_sku(nodes)
        self.assertIsNotNone(node_id, msg=("No compute nodes found"))

        # get the dmi catalog for node and fill in mock sku
        Api().nodes_get_catalog_source_by_id(identifier=node_id, source='dmi')
        node_catalog_data = loads(self.__client.last_response.data)
        self.assertGreater(len(node_catalog_data), 0, msg=("Node %s dmi catalog has zero length" % node_id))
        node_serial_number = get_by_string(node_catalog_data, 'data.Base Board Information.Serial Number').split(" ")[0]
        logs.info('Node serial number is: %s', node_serial_number)
        mock_sku['rules'][0]['contains'] = node_serial_number

        # if there is no sku associated with this node, skip copy
        if original_sku_id:
            # copy the rules from the original sku into the mock sku
            Api().skus_id_get(identifier=original_sku_id)
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)
            self.assertEqual(200, result.status, msg=result.reason)
            rules = get_by_string(data, 'rules')
            mock_sku['rules'].extend(rules)
            logs.info("Sku rules are: \n%s\n", dumps(mock_sku['rules'], indent=4))

        # POST the new sku
        logs.info("posting SKU : \n%s\n", (dumps(mock_sku, indent=4)))
        Api().skus_post(mock_sku)
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)
        sku_id = data['id']
        logs.info("ID of the posted sku is: %s", sku_id)
        self.assertEqual(201, result.status, msg=result.reason)

        # Wait fot the POSTed sku to attach
        self.wait_for_sku_to_attach(node_id, sku_id)

        # validate the /api/2.0/skus/:id/nodes works
        Api().skus_id_get_nodes(sku_id)
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)
        self.assertEqual(200, result.status, msg=result.reason)
        flag = False
        for item in data:
            if item["id"] == node_id:
                flag = True
                break
        self.assertTrue(flag, msg='Node id {} not found'.format(node_id))

        # delete the sku that where created
        logs.info(" Deleting the added sku of %s", sku_id)
        Api().skus_id_delete(identifier=sku_id)
        result = self.__client.last_response
        self.assertEqual(204, result.status, msg=result.reason)

        # if there is no sku_id, skip re-attachment tests
        if original_sku_id:
            # Wait for the original sku to re-attach
            self.wait_for_sku_to_attach(node_id, original_sku_id)

            # validate the /api/2.0/skus/:id/nodes works
            Api().skus_id_get_nodes(original_sku_id)
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)
            self.assertEqual(200, result.status, msg=result.reason)
            flag = False
            for item in data:
                if item["id"] == node_id:
                    flag = True
                    break
            self.assertTrue(flag, msg='Node id {} is not assocaited the original sku id {}'.format(node_id, original_sku_id))

    def find_node_with_sku(self, node_list):
        '''
            Find a compute node with an assocaited sku attached
            If no node is found with an attached sku, None is
            returned as the node id.

            :param node_list: list of nodes
            :return node_id, sku_id
        '''
        if node_list:
            node_id = None
            for node in node_list:
                if node.get('type') == 'compute' and node.get('sku'):
                    # update the sku rule above (rules[0].name.contains) with a value from the cataloged node
                    sku_id = node.get('sku').split("/")[4]

                    Api().skus_id_get(identifier=sku_id)
                    sku = loads(self.__client.last_response.data)

                    # this is a special case for the minnesota stacks
                    if sku.get('name') == "Unidentified-Compute":
                        continue

                    logs.info("Nodeid %s", node_id)
                    logs.info("Original node sku id %s", sku_id)

                    logs.debug("SKU dump: \n%s\n", dumps(sku, indent=4))

                    return node.get('id'), sku_id

            # no compute nodes were found with skus so find the 1st compute node
            for node in node_list:
                if node.get('type') == 'compute':
                    node_id = node.get("id")
                    logs.info("Using node without associated sku")
        return node_id, None

    def wait_for_sku_to_attach(self, node_id, sku_id):
        '''
            Wait for the provided sku to attach the the provides node
            Note: Attachment timeout or request error will cause an assert.

            :param node_id: Id of node in which the sku is to attach
            :param sku_id: Id of sku this is to attach
            :return None
        '''
        # Give enough time to wait the sku discovery finishes
        time.sleep(3)
        retries = SKU_ATTACH_WAIT_TIME
        while retries > 0:
            Api().nodes_get_by_id(identifier=node_id)
            result = self.__client.last_response
            self.assertEqual(200, result.status, msg=result.reason)

            updated_node = loads(self.__client.last_response.data)
            if updated_node['sku'] and sku_id == updated_node['sku'].split("/")[4]:
                logs.info("SKU id %s is now attached to node %s:", sku_id, node_id)
                break

            retries -= 1
            self.assertNotEqual(retries, 0, msg="Node {} never be assigned with the new sku {}".format(node_id, sku_id))
            time.sleep(1)
