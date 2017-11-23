'''
Copyright 2017, Dell, Inc.

Author(s):

UCS test script that tests:
-The Poller workflow
-The Poller data
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
class rackhd20_ucs_catalogs(unittest.TestCase):
    NODELIST = []
    RACK_NODELIST = []
    CHASSIS_NODELIST = []
    BLADE_NODELIST = []
    CATALOGS = {}

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
        api_data = fit_common.rackhdapi('/api/2.0/nodes')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for node in api_data['json']:
            if node["obms"] != [] and node["obms"][0]["service"] == "ucs-obm-service":
                self.NODELIST.append(node["id"])
                node_name = node["name"].split("/")[-1]
                if "rack" in node_name:
                    self.RACK_NODELIST.append(node["id"])
                elif "blade" in node_name:
                    self.BLADE_NODELIST.append(node["id"])
                elif "chassis" in node_name:
                    self.CHASSIS_NODELIST.append(node["id"])

    @unittest.skipUnless("ucsm_ip" in fit_common.fitcfg(), "")
    def test_check_ucs_params(self):
        if not ucs_common.is_ucs_valid():
            raise unittest.SkipTest("Ucs parameters are not valid or UCSPE emulator is not ready, skipping all UCS tests")

    @depends(after=[test_check_ucs_params])
    def test_api_20_workflow_ucs_catalogs(self):
        """
        Tests the UCS Poller workflow in rackHD
        :return:
        """
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

        header = {"Content-Type": "application/json"}
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        id = api_data["json"]["context"]["graphId"]
        status = ucs_common.wait_utility(str(id), 0, "Ucs Discovery")
        self.assertEqual(status, 'succeeded', 'Ucs Discovery graph returned status {}'.format(status))

        self.get_ucs_node_list()
        errNodes = ''
        errGraphs = ''

        for node in self.NODELIST:
            postUrl = '/api/2.0/nodes/' + node + "/workflows?name=Graph.Ucs.Catalog"
            header = {"Content-Type": "application/json"}
            api_data = fit_common.rackhdapi(postUrl, headers=header, action="post", payload={})
            if api_data['status'] != 201:
                errNodes += 'POST for node {} returned {}, '.format(node, api_data['status'])
            status = ucs_common.wait_utility(api_data["json"]["instanceId"], 0, "Catalog")
            if status != 'succeeded':
                errGraphs += 'graph id {} finished with status: {}, '.format(api_data["json"]["instanceId"], status)

            logs.info_1("Posted URL: {0} with status: {1}".format(postUrl, api_data['status']))

        self.assertEqual(len(errNodes), 0, errNodes)
        self.assertEqual(len(errGraphs), 0, errGraphs)

    @depends(after=[test_api_20_workflow_ucs_catalogs])
    def test_api_20_get_catalogs(self):
        msg = "Description: Check catalogs data per node."
        logs.info_2("\t{0}".format(msg))

        for node in self.NODELIST:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/catalogs")
            self.assertEqual(api_data['status'],
                             200,
                             "Incorrect HTTP return code, expected 200, got:{0}"
                             .format(str(api_data['status'])))
            self.CATALOGS[node] = api_data['json']
            for item in api_data['json']:
                for subitem in ['node', 'id', 'source', 'data']:
                    self.assertIn(subitem, item, subitem + ' field error')

    @depends(after=[test_api_20_get_catalogs])
    def test_api_20_verify_catalogs_source(self):
        msg = "Description: Check source of catalogs created for node"
        logs.info_2("\t{0}".format(msg))
        for node in self.NODELIST:
            sources = []
            for item in self.CATALOGS[node]:
                sources.append(item['source'])
            logs.info_5("Node {0} contains source: {1}".format(node, sources))
            self.assertIn("UCS", sources, node + " catalogs doesn't contain UCS source")
        for node in self.RACK_NODELIST + self.BLADE_NODELIST:
            sources = []
            for item in self.CATALOGS[node]:
                sources.append(item['source'])
            self.assertIn("UCS:board", sources, node + " catalogs doesn't contain UCS:board source")

    @depends(after=[test_api_20_get_catalogs])
    def test_api_20_vefify_catalogs_source_data(self):
        msg = "Description: Check source data of catalogs created for node"
        logs.info_2("\t{0}".format(msg))
        for node in self.NODELIST:
            for item in self.CATALOGS[node]:
                logs.info_2("Checking source:{0}".format(item['source']))
                self.assertNotEqual(item, '', 'Empty JSON Field')
                sourcedata = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/catalogs/" + item['source'])
                self.assertGreater(len(sourcedata['json']['id']), 0, 'id field error')
                self.assertGreater(len(sourcedata['json']['node']), 0, 'node field error')
                self.assertGreater(len(sourcedata['json']['source']), 0, 'source field error')
                self.assertGreater(len(sourcedata['json']['updatedAt']), 0, 'updatedAt field error')
                self.assertGreater(len(sourcedata['json']['createdAt']), 0, 'createdAt field error')


if __name__ == '__main__':
    unittest.main()
