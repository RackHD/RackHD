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
import test_api_utils
import ucs_common
import flogging

logs = flogging.get_loggers()


@attr(all=True, regression=True, smoke=False, ucs_rackhd=True)
class rackhd20_ucs_pollers(unittest.TestCase):
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
                nodeList.append(node["id"])
        return nodeList

    @unittest.skipUnless("ucsm_ip" in fit_common.fitcfg(), "")
    def test_check_ucs_params(self):
        if not ucs_common.is_ucs_valid():
            raise unittest.SkipTest("Ucs parameters are not valid or UCSPE emulator is not ready, skipping all UCS tests")

    @depends(after=[test_check_ucs_params])
    def test_api_20_ucs_discover_and_poller_all(self):
        """
        Tests the UCS Discovery and Poller All workflow in rackHD
        :return:
        """
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
                },
                "skip-pollers": {
                    "skipPollersCreation": "false"
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
        logs.info_1("Found {0} Nodes after pollering the UCS".format(len(api_data['json'])))

        self.assertEqual(newNodeCount - initialNodeCount,
                         expected_ucs_physical_nodes + expected_ucs_logical_nodes,
                         'Expected to discover {0} UCS nodes, got: {1}'
                         .format(expected_ucs_physical_nodes + expected_ucs_logical_nodes,
                                 newNodeCount - initialNodeCount))

    @depends(after=[test_api_20_ucs_discover_and_poller_all])
    def test_api_20_ucs_pollers(self):
        """
        Tests the UCS Poller workflow in rackHD
        :return:
        """
        # delete all previously discovered nodes and catalogs
        self.assertTrue(ucs_common.restore_node_utility(), "failed to restore nodes")
        self.assertTrue(ucs_common.restore_obms_utility(), "failed to restore obms")

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
        ucsNodes = self.get_ucs_node_list()
        errNodes = ''
        errGraphs = ''

        for node in ucsNodes:
            postUrl = '/api/2.0/nodes/' + node + "/workflows?name=Graph.Ucs.Poller"
            header = {"Content-Type": "application/json"}
            api_data = fit_common.rackhdapi(postUrl, headers=header, action="post", payload={})
            if api_data['status'] != 201:
                errNodes += 'POST for node {} returned {}, '.format(node, api_data['status'])
            status = ucs_common.wait_utility(api_data["json"]["instanceId"], 0, "Poller")
            if status != 'succeeded':
                errGraphs += 'graph id {} finished with status: {}, '.format(api_data["json"]["instanceId"], status)

            logs.info_1("Posted URL: {0} with status: {1}".format(postUrl, api_data['status']))

        self.assertEqual(len(errNodes), 0, errNodes)
        self.assertEqual(len(errGraphs), 0, errGraphs)

    @depends(after=[test_api_20_ucs_pollers])
    def test_api_20_get_pollers_by_id(self):
        ucsNodes = self.get_ucs_node_list()
        if fit_common.VERBOSITY >= 2:
            msg = "Description: Display the poller data per node."
            print("\t{0}".format(msg))

        for node in ucsNodes:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertEqual(api_data['status'],
                             200,
                             "Incorrect HTTP return code, expected 200, got:{0}"
                             .format(str(api_data['status'])))
            for item in api_data['json']:
                # check required fields
                self.assertGreater(item['pollInterval'], 0, 'pollInterval field error')
                for subitem in ['node', 'config', 'createdAt', 'id',
                                'name', 'failureCount', 'leaseExpires', 'leaseToken', 'updatedAt']:
                    self.assertIn(subitem, item, subitem + ' field error')
            if fit_common.VERBOSITY >= 2:
                print("\nNode: ")
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                print("\nPoller: " + poller + " ID: " + str(poller_id))
                poll_data = fit_common.rackhdapi("/api/2.0/pollers/" + poller_id)
                if fit_common.VERBOSITY >= 2:
                    print(fit_common.json.dumps(poll_data['json'], indent=4))

    @depends(after=[test_api_20_ucs_pollers])
    def test_api_20_vefify_pollers_data(self):
        msg = "Description: Check pollers created for node"
        if fit_common.VERBOSITY >= 2:
            print("\t{0}".format(msg))
        ucsNodes = self.get_ucs_node_list()
        errorlist = []
        poller_list = ['ucs.led', 'ucs.disk', 'ucs.psu', 'ucs.fan', 'ucs.sel', 'ucs.powerthermal']
        if fit_common.VERBOSITY >= 2:
            print("Expected Pollers for a Node: ".format(poller_list))
        for node in ucsNodes:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertIn(api_data['status'],
                          [200],
                          "Incorrect HTTP return code, expecting 200, received {}"
                          .format(api_data['status']))

            poller_dict = test_api_utils.get_supported_pollers(node)
            if set(poller_list) == set(poller_dict):
                if fit_common.VERBOSITY >= 2:
                    print("Expected pollers instantiated on node")
                if fit_common.VERBOSITY >= 3:
                    print("Poller list retreived", poller_dict)
            else:
                if list(set(poller_list) - set(poller_dict)):
                    errorlist.append("Error: Node {} Pollers not running {}"
                                     .format(node, list(set(poller_list) - set(poller_dict))))
                if list(set(poller_dict) - set(poller_list)):
                    errorlist.append("Error: Node {} Unexpected Pollers running {}"
                                     .format(node, list(set(poller_dict) - set(poller_list))))
        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print("{}".format(fit_common.json.dumps(errorlist, indent=4)))
            self.assertEqual(errorlist, [], "Error reported.")

    @depends(after=[test_api_20_ucs_pollers])
    def test_api_20_verify_poller_headers(self):
        msg = "Description: Verify header data reported on the poller"
        if fit_common.VERBOSITY >= 2:
            print("\t{0}".format(msg))
        ucsNodes = self.get_ucs_node_list()
        errorlist = []
        for node in ucsNodes:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertIn(api_data['status'],
                          [200],
                          "Incorrect HTTP return code, expecting 200, received {}".format(api_data['status']))
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                if fit_common.VERBOSITY >= 2:
                    print("Poller: {}  ID: {} ".format(poller, str(poller_id)))
                poller_data = test_api_utils.get_poller_data_by_id(poller_id)
                if poller_data == []:
                    errorlist.append("Error: Node {} Poller ID {}, {} failed to return any data"
                                     .format(node, poller_id, poller))
                if fit_common.VERBOSITY >= 3:
                    print(fit_common.json.dumps(poller_data, indent=4))

        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print("{}".format(fit_common.json.dumps(errorlist, indent=4)))
            self.assertEqual(errorlist, [], "Error reported.")

    @depends(after=[test_api_20_ucs_pollers])
    def test_api_20_verify_poller_default_cache(self):
        msg = "Description: Check number of polls being kept for poller ID"
        if fit_common.VERBOSITY >= 2:
            print("\t{0}".format(msg))
        ucsNodes = self.get_ucs_node_list()
        errorlist = []
        for node in ucsNodes:
            api_data = fit_common.rackhdapi("/api/2.0/nodes/" + node + "/pollers")
            self.assertIn(api_data['status'],
                          [200],
                          "Incorrect HTTP return code, expecting 200, received {}"
                          .format(api_data['status']))
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                poller_data = test_api_utils.get_poller_data_by_id(poller_id)
                poll_len = len(poller_data)
                if fit_common.VERBOSITY >= 2:
                    print("Poller: {}  ID: {} ".format(poller, str(poller_id)))
                    print("Number of polls for " + str(poller_id) + ": " + str(len(poller_data)))
                if poll_len > 10:
                    errorlist.append('Error: Poller {} ID: {} - Number of cached polls should not exceed 10'
                                     .format(poller_id, poller))
                elif poll_len == 0:
                    errorlist.append('Error: Poller {} ID: {} - Pollers not running'.format(poller_id, poller))
        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print("{}".format(fit_common.json.dumps(errorlist, indent=4)))
            self.assertEqual(errorlist, [], "Error reported.")

    @depends(after=[test_api_20_ucs_pollers])
    def test_api_20_verify_poller_current_data(self):
        msg = "Description: Display most current data from poller"
        if fit_common.VERBOSITY >= 2:
            print("\t{0}".format(msg))
        ucsNodes = self.get_ucs_node_list()
        errorlist = []
        for node in ucsNodes:
            poller_dict = test_api_utils.get_supported_pollers(node)
            for poller in poller_dict:
                poller_id = poller_dict[poller]["poller_id"]
                if fit_common.VERBOSITY >= 2:
                    print("Poller: {}  ID: {} ".format(poller, str(poller_id)))
                monurl = "/api/2.0/pollers/" + str(poller_id) + "/data/current"
                api_data = fit_common.rackhdapi(url_cmd=monurl)
                if api_data['status'] not in [200, 201, 202, 204]:
                    errorlist.append("Error: Node {} Poller_ID {} Failed to get current poller data, status {}"
                                     .format(node, poller_id, api_data['status']))
                else:
                    if fit_common.VERBOSITY >= 2:
                        print(fit_common.json.dumps(api_data['json'], indent=4))

        if errorlist != []:
            if fit_common.VERBOSITY >= 2:
                print("{}".format(fit_common.json.dumps(errorlist, indent=4)))
            self.assertEqual(errorlist, [], "Error reported.")


if __name__ == '__main__':
    unittest.main()
