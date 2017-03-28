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

INITIAL_NODES = {}
INITIAL_OBMS = {}


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

    UCS_IP = fit_common.fitcfg().get("ucs_ip")
    UCS_PORT = fit_common.fitcfg().get("ucs_port")
    RACKHD_IP = fit_common.fitcfg().get("rackhd_host")
    MAX_WAIT = 60
    INITIAL_CATALOGS = {}
    UCS_NODES = []
    UCS_COMPUTE_NODES = []
    EXPECTED_UCS_NODES = 22

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


    def wait_utility(self, id, counter, name):
        """
        Recursevily wait for the ucs discovery workflow to finish
        :param id:  Graph ID
        :param counter: Safeguard for the number of times we can check the status of the graph
        :param name: Description of graph we are waiting for
        :return: returns status of the taskgraph, or "timeout" if count is exceeded
        """
        api_data = fit_common.rackhdapi('/api/2.0/workflows/' + str(id))
        status = api_data["json"]["status"]
        if status == "running" and counter < self.MAX_WAIT:
            time.sleep(1)
            logs.info_1("In the wait_utility: Workflow status is {0} for the {1}'s run. ID: {2}, name: {3}"
                        .format(status, counter, id, name))
            counter += 1
            return self.wait_utility(id, counter, name)
        elif status == "running" and counter >= self.MAX_WAIT:
            logs.info_1("In the wait_utility: Timed out after trying {0} times. ID: {1}, name: {2}"
                        .format(self.MAX_WAIT, id, name))
            return 'timeout'
        else:
            logs.info_1("In the wait_utility: Waiting for workflow {0}. The status is: {1} for run: {2}. ID: {3}"
                        .format(name, status, counter, id))
            return status


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
        data_payload = {
            "name": "Graph.Ucs.Discovery",
            "options":
                {
                    "defaults":
                        {
                            "username": "ucspe",
                            "password": "ucspe",
                            "ucs": self.UCS_IP,
                            "uri": "https://" + self.RACKHD_IP + ":7080/sys"
                        }
                }
        }
        header = {"Content-Type": "application/json"}
        api_data = fit_common.rackhdapi("/api/2.0/workflows", action="post",
                                        headers=header, payload=data_payload)
        id = api_data["json"]["context"]["graphId"]
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        status = self.wait_utility(str(id), 0, "Discovery")
        self.assertEqual(status, 'succeeded', 'Discovery graph returned status {}'.format(status))
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
        for x in range(len(self.UCS_NODES)):
            postUrl = '/api/2.0/nodes/' + str(self.UCS_NODES[x]["id"]) + "/workflows?name=Graph.Ucs.Catalog"
            header = {"Content-Type": "application/json"}
            api_data = fit_common.rackhdapi(postUrl, headers=header, action="post", payload={})
            self.assertEqual(api_data['status'], 201,
                             'Expected to catalog {0} UCS nodes with status {1}, got: {2}'
                             .format(self.UCS_NODES[x]["id"], 201, api_data['status']))
            status = self.wait_utility(api_data["json"]["instanceId"], 0, "Catalog")
            self.assertEqual(status, 'succeeded', 'Catalog graph returned status {}'.format(status))

            logs.info_1("Posted URL: {0} with status: {1}".format(postUrl, api_data['status']))


if __name__ == '__main__':
    unittest.main()
