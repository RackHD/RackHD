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

logs = flogging.get_loggers()


@attr(all=True, regression=True, smoke=True, ucs=True)
class rackhd_ucs_api(unittest.TestCase):

    UCS_IP = fit_common.fitcfg().get("ucs_ip")
    UCS_PORT = fit_common.fitcfg().get("ucs_port")
    RACKHD_IP = fit_common.fitcfg().get("rackhd_host")
    MAX_WAIT = 60
    INITIAL_NODES = {}
    INITIAL_OBMS = {}
    INITIAL_CATALOGS = {}
    UCS_NODES = []
    UCS_COMPUTE_NODES = []
    EXPECTED_UCS_NODES = 22
    MAX_WAIT_ON_DELETE = 0

    def wait_utility(self, id, counter, name):
        """
        Recursevily wait for the ucs discovery workflow to finish
        :param id:  Graph ID
        :param counter: Safeguard for the number of times we can check the status of the graph
        :param name: Description of graph we are waiting for
        :return: return False on failure, or True otherwise
        """
        api_data = fit_common.rackhdapi('/api/2.0/workflows/' + str(id))
        status = api_data["json"]["status"]
        if status == "running" and counter < self.MAX_WAIT:
            time.sleep(1)
            logs.info_1("In the wait_utility: Workflow status is {0} for the {1}'s run. ID: {2}, name: {3}"
                        .format(status, counter, id, name))
            counter += 1
            self.wait_utility(id, counter, name)
        elif status == "running" and counter >= self.MAX_WAIT:
            logs.info_1("In the wait_utility: Timed out after trying {0} times. ID: {1}, name: {2}"
                        .format(self.MAX_WAIT, id, name))
            return False
        else:
            logs.info_1("In the wait_utility: Waiting for workflow {0}. The status is: {1} for run: {2}. ID: {3}"
                        .format(name, status, counter, id))
            return True

    def get_nodes_utility(self):
        """
        Takes inventory of the nodes available before discovering the UCS nodes.
        We will restore the nodes collection to this snapshot
        :return:
        """
        api_data = fit_common.rackhdapi('/api/2.0/nodes')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for node in api_data['json']:
            self.INITIAL_NODES[node['id']] = node['type']
        logs.info_1("Found {0} Nodes before cataloging the UCS. {1}"
                    .format(len(self.INITIAL_NODES), self.INITIAL_NODES))

    def get_obms_utility(self):
        """
        Takes inventory of the obms available before discovering the UCS obms.
        We will restore the obms collection to this snapshot.
        :return:
        """
        api_data = fit_common.rackhdapi('/api/2.0/obms')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        for obm in api_data['json']:
            self.INITIAL_OBMS[obm['id']] = obm['service']
        logs.info_1("Found {0} obms before cataloging the UCS: {1}".format(len(self.INITIAL_OBMS), self.INITIAL_OBMS))

    def restore_node_utility(self, catalog_workflows):
        """
        Deletes all the added ucs nodes by the test.
        :param catalog_workflows: A list of the catalog workflow IDs that will wait for their completion .
        :return:
        """
        logs.info_1("Restoring Nodes")
        api_data = fit_common.rackhdapi('/api/2.0/nodes')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for catalog_workflow in catalog_workflows:
            self.wait_utility(str(catalog_workflow), 0, "Catalog")
        for node in api_data['json']:
            if node['id'] not in self.INITIAL_NODES:
                api_data = fit_common.rackhdapi('/api/2.0/nodes/' + node['id'], action="delete")
                logs.info_1("Deleting Node: {0}. Status was: {1}".format(node['id'], api_data['status']))
                time.sleep(self.MAX_WAIT_ON_DELETE)

        api_data = fit_common.rackhdapi('/api/2.0/nodes')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        temp = {}
        for node in api_data['json']:
            temp[node['id']] = node['name']

        self.assertEqual(len(temp), len(self.INITIAL_NODES),
                         "Found {0}  nodes remaining after restoring the nodes, should be {1}, Remaining nodes: {2}"
                         .format(len(temp), len(self.INITIAL_NODES), temp))

    def restore_obms_utility(self):
        """
         Deletes all the added ucs obms by this test.
        :return:
        """
        logs.info_1("Restoring OBMs")
        api_data = fit_common.rackhdapi('/api/2.0/obms')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        for obm in api_data['json']:
            if obm['id'] not in self.INITIAL_OBMS:
                api_data = fit_common.rackhdapi('/api/2.0/obms/' + obm['id'], action="delete")
                logs.info_1("Deleting OBM: {0}. Status was: {1}".format(obm['id'], str(api_data['status'])))
                time.sleep(self.MAX_WAIT_ON_DELETE)
        api_data = fit_common.rackhdapi('/api/2.0/obms')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        temp = {}
        for obm in api_data['json']:
            temp[obm['id']] = obm['service']
        self.assertEqual(len(temp), len(self.INITIAL_OBMS),
                         "Found {0} ucs obms remaining after restoring the obms, should be {1}. Remaining OBMs: {2}"
                         .format(len(temp), len(self.INITIAL_OBMS), temp))

    def ucs_url_factory(self, api, identifier=None):
        """
        returns a fully qualified UCS API
        :param api:UCS API
        :param identifier: identify the ucs element in the catalog API
        :return:
        """
        ucs_service = self.RACKHD_IP + ":" + self.UCS_PORT + "/"
        ucs_manager = self.UCS_IP
        if identifier is None:
            url = "http://" + ucs_service + api + "?host=" + ucs_manager + " &user=ucspe&password=ucspe"
        else:
            url = "http://" + ucs_service + api + "?host=" + ucs_manager + " &user=ucspe&password=ucspe"\
                  "&identifier=" + identifier
        return url

    @unittest.skipUnless("ucs_ip" in fit_common.fitcfg(), "")
    def test_check_ucs_params(self):
        self.assertNotEqual(self.UCS_IP, None, "Expected value for UCS_IP other then None and found {0}"
                            .format(self.UCS_IP))
        self.assertNotEqual(self.UCS_PORT, None, "Expected value for UCS_PORT other then None and found {0}"
                            .format(self.UCS_IP))

    @depends(after=test_check_ucs_params)
    def test_api_20_ucs_discovery(self):
        """
        Tests the UCS Discovery workflow in rackHD
        :return:
        """
        self.get_nodes_utility()
        self.get_obms_utility()

        data_payload = {
            "name": "Graph.Ucs.Discovery",
            "options":
                {
                    "defaults":
                        {
                            "username": "ucspe",
                            "password": "ucspe",
                            "ucs": self.UCS_IP,
                            "uri": "http://" + self.RACKHD_IP + ":7080/sys"
                        }
                }
        }
        header = {"Content-Type": "application/json"}
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        self.wait_utility(str(id), 0, "Discovery")
        api_data = fit_common.rackhdapi('/api/2.0/nodes')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        logs.info_1("Found {0} Nodes after cataloging the UCS".format(len(api_data['json'])))

        for node in api_data['json']:
            if node["obms"] != [] and node["obms"][0]["service"] == "ucs-obm-service":
                self.UCS_NODES.append(node)
                if node["type"] == "compute":
                    self.UCS_COMPUTE_NODES.append(node)
        self.assertGreaterEqual(len(self.UCS_NODES), self.EXPECTED_UCS_NODES,
                                'Expected to discover {0} UCS nodes, got: {1}'
                                .format(self.EXPECTED_UCS_NODES, len(self.UCS_NODES)))
        logs.info_1("Found {0} UCS nodes {1}".format(len(self.UCS_COMPUTE_NODES), self.UCS_COMPUTE_NODES))

    @depends(after=[test_check_ucs_params, test_api_20_ucs_discovery])
    def test_api_20_ucs_catalog(self):
        """
        Tests the UCS Catalog workflow in rackHD
        :return:
        """
        catalog_workflows = []
        for x in range(len(self.UCS_NODES)):
            postUrl = '/api/1.1/nodes/' + str(self.UCS_NODES[x]["id"]) + "/workflows?name=Graph.Ucs.Catalog"
            header = {"Content-Type": "application/json"}
            api_data = fit_common.rackhdapi(postUrl, headers=header, action="post")
            self.assertEqual(api_data['status'], 201,
                             'Expected to catalog {0} UCS nodes with status {1}, got: {2}'
                             .format(self.UCS_NODES[x]["id"], 201, api_data['status']))
            catalog_workflows.append(api_data["json"]["instanceId"])
            logs.info_1("Posted URL: {0} with status: {1}".format(postUrl, api_data['status']))

        # Restore the nodes, obms, and catalogs to their state before the UCS discovery
        # in order to avoid any failure in other tests
        logs.info_1("Restoring the database to the state it was in before the UCS discovery and catalog")
        self.restore_node_utility(catalog_workflows)
        self.restore_obms_utility()


if __name__ == '__main__':
    unittest.main()
