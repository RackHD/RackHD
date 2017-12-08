'''
Copyright 2017, Dell, Inc.

Author(s):

UCS test script that tests:
-The Discovery workflow
-The Catalog workflow
'''

import fit_path  # NOQA: unused import
import unittest
from common import fit_common
from nosedep import depends
from nose.plugins.attrib import attr
import ucs_common
import flogging

logs = flogging.get_loggers()


@attr(all=True, regression=True, smoke=False, ucs_rackhd=True)
class rackhd20_ucs_discovery(unittest.TestCase):
    UCS_COMPUTE_NODES = []

    @classmethod
    def setUpClass(cls):
        if not ucs_common.get_nodes_utility():
            raise Exception("error getting node list")
        if not ucs_common.get_obms_utility():
            raise Exception("error getting obms list")

    @classmethod
    def tearDownClass(cls):
        if not ucs_common.restore_node_utility():
            raise Exception("error restoring node list")
        if not ucs_common.restore_obms_utility():
            raise Exception("error restoring obms list")

    def get_ucs_node_list(self):
        nodeList = []
        api_data = fit_common.rackhdapi('/api/2.0/nodes')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for node in api_data['json']:
            if node["obms"] != [] and node["obms"][0]["service"] == "ucs-obm-service":
                nodeList.append(node)
        return (nodeList)

    def get_ucs_encl_id_list(self):
        enclIdList = []
        nodeList = self.get_ucs_node_list()
        for node in nodeList:
            if node["type"] == 'enclosure':
                enclIdList.append(node['id'])
        return (enclIdList)

    @unittest.skipUnless("ucsm_ip" in fit_common.fitcfg(), "")
    def test_check_ucs_params(self):
        if not ucs_common.is_ucs_valid():
            raise unittest.SkipTest("Ucs parameters are not valid or UCSPE emulator is not ready, skipping all UCS tests")

    @depends(after=test_check_ucs_params)
    def test_api_20_ucs_discovery(self):
        """
        Tests the UCS Discovery workflow in rackHD
        :return:
        """

        initialNodeCount = len(self.get_ucs_node_list())
        data_payload = {
            "name": "Graph.Ucs.Discovery",
            "options": {
                "defaults": {
                    "username": ucs_common.UCSM_USER,
                    "password": ucs_common.UCSM_PASS,
                    "ucs": ucs_common.UCSM_IP,
                    "uri": ucs_common.UCS_SERVICE_URI
                },
                "when-discover-physical-ucs": {
                    "discoverPhysicalServers": "true",
                },
                "when-discover-logical-ucs": {
                    "discoverLogicalServer": "false"
                },
                "when-catalog-ucs": {
                    "autoCatalogUcs": "false"
                }
            }
        }

        expected_ucs_physical_nodes = ucs_common.get_physical_server_count()
        header = {"Content-Type": "application/json"}
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = ucs_common.wait_utility(str(id), 0, "Discovery")
        self.assertEqual(status, 'succeeded', 'Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())
        logs.info_1("Found {0} Nodes after cataloging the UCS".format(len(api_data['json'])))

        self.assertEqual(newNodeCount - initialNodeCount,
                         expected_ucs_physical_nodes,
                         'Expected to discover {0} UCS nodes, got: {1}'
                         .format(expected_ucs_physical_nodes, newNodeCount - initialNodeCount))

        # rerun discovery and verify duplicate nodes are not created
        initialNodeCount = len(self.get_ucs_node_list())
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = ucs_common.wait_utility(str(id), 0, "Discovery")
        self.assertEqual(status, 'succeeded', 'Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())
        logs.info_1("Found {0} Nodes after cataloging the UCS".format(len(api_data['json'])))

        self.assertEqual(newNodeCount - initialNodeCount, 0,
                                'Expected to discover {0} UCS nodes, got: {1}'
                                .format(0, newNodeCount - initialNodeCount))

    @depends(after=[test_api_20_ucs_discovery])
    @unittest.skip("Skipping 'test_api_redfish_chassis' bug RAC-5358")
    def test_api_redfish_chassis(self):
        """
        Tests the redfish/chassis routes with UCS nodes
        :return:
        """
        ucsEnclList = self.get_ucs_encl_id_list()
        errUrls = ''

        api_data = fit_common.rackhdapi('/redfish/v1/Chassis')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for chassis in api_data['json']['Members']:
            url = chassis['@odata.id']
            id = url[len('/redfish/v1/Chassis/'):]
            if id in ucsEnclList:
                ucsEnclList.remove(id)
                api_data = fit_common.rackhdapi(url)
                if api_data['status'] != 200:
                    errUrls += url + ' returned status ' + str(api_data['status']) + ',\n'
        self.assertEqual(len(ucsEnclList), 0, 'not all UCS chassis were listed under /chassis')
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_20_ucs_discovery])
    def test_api_20_ucs_discover_and_catalog_all(self):
        """
        Tests the UCS Discovery and Catalon All workflow in rackHD
        :return:
        """
        # delete all previously discovered nodes and catalogs
        self.assertTrue(ucs_common.restore_node_utility(), "failed to restore nodes")
        self.assertTrue(ucs_common.restore_obms_utility(), "failed to restore obms")

        initialNodeCount = len(self.get_ucs_node_list())
        expected_ucs_logical_nodes = ucs_common.get_service_profile_count()
        expected_ucs_physical_nodes = ucs_common.get_physical_server_count()

        data_payload = {
            "name": "Graph.Ucs.Discovery",
            "options": {
                "defaults": {
                    "username": ucs_common.UCSM_USER,
                    "password": ucs_common.UCSM_PASS,
                    "ucs": ucs_common.UCSM_IP,
                    "uri": ucs_common.UCS_SERVICE_URI
                },
                "when-discover-physical-ucs": {
                    "discoverPhysicalServers": "true",
                },
                "when-discover-logical-ucs": {
                    "discoverLogicalServer": "true"
                },
                "when-catalog-ucs": {
                    "autoCatalogUcs": "true"
                }
            }
        }

        header = {"Content-Type": "application/json"}
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = ucs_common.wait_utility(str(id), 0, "Discovery", 240)
        self.assertEqual(status, 'succeeded', 'Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())

        logs.info_1("Found {0} Nodes after cataloging the UCS".format(len(api_data['json'])))

        self.assertEqual(newNodeCount - initialNodeCount,
                         expected_ucs_physical_nodes + expected_ucs_logical_nodes,
                         'Expected to discover {0} UCS nodes, got: {1}'
                         .format(expected_ucs_physical_nodes + expected_ucs_logical_nodes,
                                 newNodeCount - initialNodeCount))

    @depends(after=test_api_20_ucs_discover_and_catalog_all)
    def test_api_20_ucs_serviceProfile_discovery(self):
        """
        Tests the UCS Service Profile Discovery workflow in rackHD
        :return:
        """
        # delete all previously discovered nodes and catalogs
        self.assertTrue(ucs_common.restore_node_utility(), "failed to restore nodes")
        self.assertTrue(ucs_common.restore_obms_utility(), "failed to restore obms")

        expected_ucs_logical_nodes = ucs_common.get_service_profile_count()
        if (expected_ucs_logical_nodes == 0):
            raise unittest.SkipTest("No Service Profiles Defined")

        initialNodeCount = len(self.get_ucs_node_list())

        data_payload = {
            "name": "Graph.Ucs.Discovery",
            "options": {
                "defaults": {
                    "username": ucs_common.UCSM_USER,
                    "password": ucs_common.UCSM_PASS,
                    "ucs": ucs_common.UCSM_IP,
                    "uri": ucs_common.UCS_SERVICE_URI
                },
                "when-discover-physical-ucs": {
                    "discoverPhysicalServers": "false",
                },
                "when-discover-logical-ucs": {
                    "discoverLogicalServer": "true"
                },
                "when-catalog-ucs": {
                    "autoCatalogUcs": "false"
                }
            }
        }

        header = {"Content-Type": "application/json"}
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        id = api_data["json"]["context"]["graphId"]
        status = ucs_common.wait_utility(str(id), 0, "Service Profile Discovery")
        self.assertEqual(status, 'succeeded', 'Service Profile Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())

        self.assertEqual(newNodeCount - initialNodeCount,
                         expected_ucs_logical_nodes,
                         'Expected to discover {0} UCS nodes, got: {1}'
                         .format(expected_ucs_logical_nodes, newNodeCount - initialNodeCount))
        logs.info_1("Found {0} UCS nodes {1}".format(len(self.UCS_COMPUTE_NODES), self.UCS_COMPUTE_NODES))

        # rerun discovery graph and verify duplicate nodes are not created
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = ucs_common.wait_utility(str(id), 0, "Service Profile Discovery")
        self.assertEqual(status, 'succeeded', 'Service Profile Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())
        self.assertGreaterEqual(newNodeCount - initialNodeCount, 0,
                                'Expected to discover {0} UCS nodes, got: {1}'
                                .format(0, newNodeCount - initialNodeCount))


if __name__ == '__main__':
    unittest.main()
