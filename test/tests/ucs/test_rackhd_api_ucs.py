'''
Copyright 2017, Dell, Inc.

Author(s):

UCS test script that tests:
-All the ucs service APIs
-The Discovery workflow
-The Catalog workflow

'''

import fit_path  # NOQA: unused import
import unittest
from common import fit_common
import time
from nosedep import depends
import flogging
from nose.plugins.attrib import attr
from config.settings import get_ucs_cred

logs = flogging.get_loggers()

INITIAL_NODES = {}
INITIAL_OBMS = {}
UCSM_IP = fit_common.fitcfg().get('ucsm_ip')
UCSM_USER, UCSM_PASS = get_ucs_cred()
UCS_SERVICE_URI = fit_common.fitcfg().get('ucs_service_uri')


def get_nodes_utility():
    """
    Takes inventory of the nodes available before discovering the UCS nodes.
    We will restore the nodes collection to this snapshot
    :return: return False on failure, or True otherwise
    """
    api_data = fit_common.rackhdapi('/api/2.0/nodes')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/nodes returned status {}, expected 200".format(api_data['status']))
        return False

    for node in api_data['json']:
        INITIAL_NODES[node['id']] = node['type']
    logs.info_1("Found {0} Nodes before cataloging the UCS. {1}"
                .format(len(INITIAL_NODES), INITIAL_NODES))
    return True


def get_obms_utility():
    """
    Takes inventory of the obms available before discovering the UCS obms.
    We will restore the obms collection to this snapshot.
    :return: return False on failure, or True otherwise
    """
    api_data = fit_common.rackhdapi('/api/2.0/obms')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/obms returned status {}, expected 200".format(api_data['status']))
        return False

    for obm in api_data['json']:
        INITIAL_OBMS[obm['id']] = obm['service']
    logs.info_1("Found {0} obms before cataloging the UCS: {1}".format(len(INITIAL_OBMS), INITIAL_OBMS))
    return True


def restore_node_utility():
    """
    Deletes all the added ucs nodes by the test.
    :return: return False on failure, or True otherwise
    """
    logs.info_1("Restoring Nodes")
    api_data = fit_common.rackhdapi('/api/2.0/nodes')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/nodes returned status {}, expected 200".format(api_data['status']))
        return False

    for node in api_data['json']:
        if node['id'] not in INITIAL_NODES:
            api_data = fit_common.rackhdapi('/api/2.0/nodes/' + node['id'], action="delete")
            logs.info_1("Deleting Node: {0}. Status was: {1}".format(node['id'], api_data['status']))

    api_data = fit_common.rackhdapi('/api/2.0/nodes')

    if api_data['status'] != 200:
        logs.error("get /api/2.0/nodes returned status {}, expected 200".format(api_data['status']))
        return False

    temp = {}
    for node in api_data['json']:
        temp[node['id']] = node['name']

    if len(temp) != len(INITIAL_NODES):
        logs.error("Found {0}  nodes remaining after restoring the nodes, should be {1}, Remaining nodes: {2}"
                   .format(len(temp), len(INITIAL_NODES), temp))
        return False

    return True


def restore_obms_utility():
    """
     Deletes all the added ucs obms by this test.
    :return:
    """
    logs.info_1("Restoring OBMs")

    api_data = fit_common.rackhdapi('/api/2.0/obms')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/obms returned status {}, expected 200".format(api_data['status']))
        return False

    for obm in api_data['json']:
        if obm['id'] not in INITIAL_OBMS:
            api_data = fit_common.rackhdapi('/api/2.0/obms/' + obm['id'], action="delete")
            logs.info_1("Deleting OBM: {0}. Status was: {1}".format(obm['id'], str(api_data['status'])))

    api_data = fit_common.rackhdapi('/api/2.0/obms')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/obms returned status {}, expected 200".format(api_data['status']))
        return False

    temp = {}
    for obm in api_data['json']:
        temp[obm['id']] = obm['service']
    if len(temp) != len(INITIAL_OBMS):
        logs.error("Found {0} ucs obms remaining after restoring the obms, should be {1}. Remaining OBMs: {2}"
                   .format(len(temp), len(INITIAL_OBMS), temp))
        return False

    return True


@attr(all=True, regression=True, smoke=True, ucs_rackhd=True)
class rackhd_ucs_api(unittest.TestCase):

    MAX_WAIT = 180
    INITIAL_CATALOGS = {}
    UCS_NODES = []
    UCS_COMPUTE_NODES = []
    EXPECTED_UCS_PHYSICAL_NODES = 22
    EXPECTED_UCS_LOGICAL_NODES = 18

    @classmethod
    def setUpClass(cls):
        if not get_nodes_utility():
            raise Exception("error getting node list")
        if not get_obms_utility():
            raise Exception("error getting obms list")

    @classmethod
    def tearDownClass(cls):
        if not restore_node_utility():
            raise Exception("error restoring node list")
        if not restore_obms_utility():
            raise Exception("error restoring obms list")

    def get_physical_server_count(self):
        """
        Get a count of the number of Service Proviles defined by the UCS Manager
        """
        url = UCS_SERVICE_URI + "/rackmount"

        headers = {"ucs-user": UCSM_USER,
                   "ucs-password": UCSM_PASS,
                   "ucs-host": UCSM_IP}

        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        count = len(api_data["json"])

        url = UCS_SERVICE_URI + "/chassis"
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        count += len(api_data["json"])
        for element in api_data["json"]:
            count += len(element["members"])

        return count

    def get_service_profile_count(self):
        """
        Get a count of the number of Service Proviles defined by the UCS Manager
        """
        url = UCS_SERVICE_URI + "/serviceProfile"
        headers = {"ucs-user": UCSM_USER,
                   "ucs-password": UCSM_PASS,
                   "ucs-host": UCSM_IP}

        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        return len(api_data["json"]["ServiceProfile"]["members"])

    def wait_utility(self, id, counter, name, max_wait=MAX_WAIT):
        """
        Recursevily wait for the ucs discovery workflow to finish
        :param id:  Graph ID
        :param counter: Safeguard for the number of times we can check the status of the graph
        :param name: Description of graph we are waiting for
        :return: returns status of the taskgraph, or "timeout" if count is exceeded
        """
        api_data = fit_common.rackhdapi('/api/2.0/workflows/' + str(id))
        status = api_data["json"]["status"]
        if status == "running" and counter < max_wait:
            time.sleep(1)
            logs.info_1("In the wait_utility: Workflow status is {0} for the {1}'s run. ID: {2}, name: {3}"
                        .format(status, counter, id, name))
            counter += 1
            return self.wait_utility(id, counter, name, max_wait)
        elif status == "running" and counter >= max_wait:
            logs.info_1("In the wait_utility: Timed out after trying {0} times. ID: {1}, name: {2}"
                        .format(max_wait, id, name))
            return 'timeout'
        else:
            logs.info_1("In the wait_utility: Waiting for workflow {0}. The status is: {1} for run: {2}. ID: {3}"
                        .format(name, status, counter, id))
            return status

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
        self.assertNotEqual(UCSM_IP, None, "Expected value for UCSM_IP other then None and found {0}"
                            .format(UCSM_IP))
        self.assertNotEqual(UCS_SERVICE_URI, None,
                            "Expected value for UCS_SERVICE_URI other then None and found {0}"
                            .format(UCS_SERVICE_URI))

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
                    "username": UCSM_USER,
                    "password": UCSM_PASS,
                    "ucs": UCSM_IP,
                    "uri": UCS_SERVICE_URI
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

        expected_ucs_physical_nodes = self.get_physical_server_count()

        header = {"Content-Type": "application/json"}
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = self.wait_utility(str(id), 0, "Discovery")
        self.assertEqual(status, 'succeeded', 'Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())

        logs.info_1("Found {0} Nodes after cataloging the UCS".format(len(api_data['json'])))

        self.assertEqual(newNodeCount - initialNodeCount, expected_ucs_physical_nodes,
                                'Expected to discover {0} UCS nodes, got: {1}'
                                .format(expected_ucs_physical_nodes, newNodeCount - initialNodeCount))

        # rerun discovery and verify duplicate nodes are not created
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = self.wait_utility(str(id), 0, "Discovery")
        self.assertEqual(status, 'succeeded', 'Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())

        logs.info_1("Found {0} Nodes after cataloging the UCS".format(len(api_data['json'])))

        self.assertGreaterEqual(newNodeCount - initialNodeCount, 0,
                                'Expected to discover {0} UCS nodes, got: {1}'
                                .format(0, newNodeCount - initialNodeCount))

    @depends(after=test_api_20_ucs_discovery)
    def test_api_20_ucs_serviceProfile_discovery(self):
        """
        Tests the UCS Service Profile Discovery workflow in rackHD
        :return:
        """
        expected_ucs_logical_nodes = self.get_service_profile_count()
        if (expected_ucs_logical_nodes == 0):
            raise unittest.SkipTest("No Service Profiles Defined")

        initialNodeCount = len(self.get_ucs_node_list())

        data_payload = {
            "name": "Graph.Ucs.Discovery",
            "options": {
                "defaults": {
                    "username": UCSM_USER,
                    "password": UCSM_PASS,
                    "ucs": UCSM_IP,
                    "uri": UCS_SERVICE_URI
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
        status = self.wait_utility(str(id), 0, "Service Profile Discovery")
        self.assertEqual(status, 'succeeded', 'Service Profile Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())

        self.assertEqual(newNodeCount - initialNodeCount, expected_ucs_logical_nodes,
                                'Expected to discover {0} UCS nodes, got: {1}'
                                .format(expected_ucs_logical_nodes, newNodeCount - initialNodeCount))
        logs.info_1("Found {0} UCS nodes {1}".format(len(self.UCS_COMPUTE_NODES), self.UCS_COMPUTE_NODES))

        # rerun discovery graph and verify duplicate nodes are not created
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = self.wait_utility(str(id), 0, "Service Profile Discovery")
        self.assertEqual(status, 'succeeded', 'Service Profile Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())

        self.assertGreaterEqual(newNodeCount - initialNodeCount, 0,
                                'Expected to discover {0} UCS nodes, got: {1}'
                                .format(0, newNodeCount - initialNodeCount))

    @depends(after=[test_api_20_ucs_discovery])
    def test_api_20_ucs_catalog(self):
        """
        Tests the UCS Catalog workflow in rackHD
        :return:
        """

        ucsNodes = self.get_ucs_node_list()
        errNodes = ''
        errGraphs = ''

        for x in range(len(ucsNodes)):
            postUrl = '/api/2.0/nodes/' + str(ucsNodes[x]["id"]) + "/workflows?name=Graph.Ucs.Catalog"
            header = {"Content-Type": "application/json"}
            api_data = fit_common.rackhdapi(postUrl, headers=header, action="post", payload={})
            if api_data['status'] != 201:
                errNodes += 'POST for node {} returned {}, '.format(ucsNodes[x]['id'], api_data['status'])
            status = self.wait_utility(api_data["json"]["instanceId"], 0, "Catalog")
            if status != 'succeeded':
                errGraphs += 'graph id {} finished with status: {}, '.format(api_data["json"]["instanceId"], status)

            logs.info_1("Posted URL: {0} with status: {1}".format(postUrl, api_data['status']))

        self.assertEqual(len(errNodes), 0, errNodes)
        self.assertEqual(len(errGraphs), 0, errGraphs)

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

    @depends(after=[test_api_20_ucs_catalog])
    def test_api_20_ucs_discover_and_catalog_all(self):
        """
        Tests the UCS Discovery and Catalon All workflow in rackHD
        :return:
        """

        # delete all previously discovered nodes and catalogs
        self.assertTrue(restore_node_utility(), "failed to restore nodes")
        self.assertTrue(restore_obms_utility(), "failed to restore obms")

        initialNodeCount = len(self.get_ucs_node_list())
        expected_ucs_logical_nodes = self.get_service_profile_count()
        expected_ucs_physical_nodes = self.get_physical_server_count()

        data_payload = {
            "name": "Graph.Ucs.Discovery",
            "options": {
                "defaults": {
                    "username": UCSM_USER,
                    "password": UCSM_PASS,
                    "ucs": UCSM_IP,
                    "uri": UCS_SERVICE_URI
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
        status = self.wait_utility(str(id), 0, "Discovery", 240)
        self.assertEqual(status, 'succeeded', 'Discovery graph returned status {}'.format(status))

        newNodeCount = len(self.get_ucs_node_list())

        logs.info_1("Found {0} Nodes after cataloging the UCS".format(len(api_data['json'])))

        self.assertEqual(newNodeCount - initialNodeCount,
                         expected_ucs_physical_nodes + expected_ucs_logical_nodes,
                         'Expected to discover {0} UCS nodes, got: {1}'
                         .format(expected_ucs_physical_nodes + expected_ucs_logical_nodes,
                                 newNodeCount - initialNodeCount))


if __name__ == '__main__':
    unittest.main()
