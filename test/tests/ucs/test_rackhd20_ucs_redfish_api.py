'''
Copyright 2017, Dell, Inc.

Author(s):

UCS test script that tests:
-Redfish API for UCS nodes
'''

import fit_path  # NOQA: unused import
import unittest
from common import fit_common
from nosedep import depends
from nose.plugins.attrib import attr
import ucs_common
import flogging
import re

logs = flogging.get_loggers()


@attr(all=True, regression=True, smoke=False, ucs_rackhd=True)
class rackhd20_ucs_redfish_api(unittest.TestCase):
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

    def get_ucs_compute_id_list(self):
        enclIdList = []
        nodeList = self.get_ucs_node_list()
        for node in nodeList:
            if node["type"] == 'compute':
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
                "when-discover-logical-ucs": {
                    "discoverLogicalServer": "false"
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

    @depends(after=[test_api_20_ucs_discovery])
    def test_api_redfish_chassis(self):
        """
        Tests the redfish /Chassis APIs with UCS nodes
        :return:
        """
        ucsEnclList = self.get_ucs_encl_id_list()
        errUrls = ''

        def validate_chassis_data(body, url):
            """
            Validate system non-empty data body
            """
            errData = ''
            str_keys = ["Name", "ChassisType", "Manufacturer", "Model", "SerialNumber",
                        "IndicatorLED"]
            dict_keys = ["Thermal", "Power", "Links"]
            for key in str_keys:
                value = body[key]
                if not isinstance(value, unicode) or not value:
                    errData += "Invalid System {} \"{}\" for {}, \n".format(key, value, url)
            for key in dict_keys:
                value = body[key]
                if not isinstance(value, dict) or not value:
                    errData += "Invalid System {} \"{}\" for {}, \n".format(key, value, url)
            return errData

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
                _body = api_data['json']
                errData = validate_chassis_data(_body, url)
                if errData:
                    errUrls += errData
        self.assertEqual(len(ucsEnclList), 0, 'not all UCS chassis were listed under /chassis')
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_redfish_chassis])
    def test_api_redfish_chassis_thermal(self):
        """
        Tests the redfish /Chassis/{identifier}/Thermal APIs with UCS nodes
        :return:
        """
        ucsEnclList = self.get_ucs_encl_id_list()
        errUrls = ''
        for chassis in ucsEnclList:
            url = '/redfish/v1/Chassis/{}/Thermal'.format(chassis)
            api_data = fit_common.rackhdapi(url)
            if api_data['status'] != 200:
                errUrls += url + ' returned status ' + str(api_data['status']) + ',\n'
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_redfish_chassis])
    def test_api_redfish_chassis_power(self):
        """
        Tests the redfish /Chassis/{identifier}/Power APIs with UCS nodes
        :return:
        """
        ucsEnclList = self.get_ucs_encl_id_list()
        errUrls = ''
        for chassis in ucsEnclList:
            url = '/redfish/v1/Chassis/{}/Power'.format(chassis)
            api_data = fit_common.rackhdapi(url)
            if api_data['status'] != 200:
                errUrls += url + ' returned status ' + str(api_data['status']) + ',\n'
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_20_ucs_discovery])
    def test_api_redfish_system(self):
        """
        Tests the redfish /Systems APIs with UCS nodes
        :return:
        """
        ucsComputeList = self.get_ucs_compute_id_list()
        errUrls = ''

        def validate_system_data(body, url):
            """
            Validate system non-empty data body
            """
            errData = ''
            str_keys = ["Name", "SystemType", "Manufacturer", "Model", "SerialNumber",
                        "IndicatorLED", "PowerState", "BiosVersion"]
            dict_keys = ["ProcessorSummary", "MemorySummary", "Actions", "Processors",
                         "EthernetInterfaces", "SimpleStorage", "LogServices", "Links", "Storage"]
            for key in str_keys:
                value = body[key]
                if not isinstance(value, unicode) or not value:
                    errData += "Invalid System {} \"{}\" for {}, \n".format(key, value, url)
            for key in dict_keys:
                value = body[key]
                if not isinstance(value, dict) or not value:
                    errData += "Invalid System {} \"{}\" for {}, \n".format(key, value, url)
            return errData

        api_data = fit_common.rackhdapi('/redfish/v1/Systems')
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for chassis in api_data['json']['Members']:
            url = chassis['@odata.id']
            id = url[len('/redfish/v1/Systems/'):]
            if id in ucsComputeList:
                ucsComputeList.remove(id)
                api_data = fit_common.rackhdapi(url)
                if api_data['status'] != 200:
                    errUrls += url + ' returned status ' + str(api_data['status']) + ',\n'
                _body = api_data['json']
                errData = validate_system_data(_body, url)
                if errData:
                    errUrls += errData
        self.assertEqual(len(ucsComputeList), 0, 'not all UCS computes were listed under /System')
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_redfish_system])
    def test_api_redfish_processor(self):
        """
        Tests the /Systems/{identifier}/processors APIs with UCS nodes
        :return:
        """
        ucsComputeList = self.get_ucs_compute_id_list()
        errUrls = ''

        def validate_cpu_data(body, url):
            """
            Validate processor data body
            """
            errData = ''
            int_keys = ["MaxSpeedMHz", "TotalCores", "TotalThreads"]
            str_keys = ["Socket", "ProcessorType", "ProcessorArchitecture",
                        "InstructionSet", "Manufacturer", "Model"]
            for key in int_keys:
                value = body[key]
                if not isinstance(value, int) or value <= 0:
                    errData += "Invalid Processor {} \"{}\" for {}, \n".format(key, value, url)
            for key in str_keys:
                value = body[key]
                if not isinstance(value, unicode) or not value:
                    errData += "Invalid Processor {} \"{}\" for {}, \n".format(key, value, url)
            return errData

        for node in ucsComputeList:
            url = "/redfish/v1/Systems/{}/Processors".format(node)
            api_data = fit_common.rackhdapi(url)
            if api_data['status'] != 200:
                errUrls += url + ' returned status ' + str(api_data['status']) + \
                    ', Expected 200,\n'
                continue
            if len(api_data['json']['Members']) == 0:
                errUrls += url + ' CPU count is 0,\n'
                continue
            if len(api_data['json']['Members']) != api_data['json']['Members@odata.count']:
                errUrls += url + ' CPU count is {}, Expected {}\n'.format(
                    api_data['json']['Members@odata.count'], len(api_data['json']['Members'])
                )
                continue
            for member in api_data['json']['Members']:
                _url = member['@odata.id']
                _api_data = fit_common.rackhdapi(_url)
                if _api_data['status'] != 200:
                    errUrls += _url + ' returned status ' + str(api_data['status']) + \
                        ', Expected 200,\n'
                _body = _api_data['json']
                errData = validate_cpu_data(_body, _url)
                if errData:
                    errUrls += errData
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_redfish_system])
    def test_api_redfish_simple_storage(self):
        """
        Tests the redfish /Systems/{identifier}/simpleStorage APIs with UCS nodes
        :return:
        """
        ucsComputeList = self.get_ucs_compute_id_list()
        errUrls = ''

        def validate_simple_storage_data(body, url):
            """
            Validate simple storage non-empty data body
            """
            errData = ''
            str_keys = ["Name", "Id", "Description"]
            for key in str_keys:
                value = body[key]
                if not isinstance(value, unicode) or not value:
                    errData += "Invalid simpleStorage {} \"{}\" for {}, \n".format(key, value, url)
            if not re.compile('^\w{0,}_\w{1,3}_\w{1,}_\w{1}$').match(body['Id']):
                errData += "Invalid simpleStorage Id \"{}\" for {}, \n".format(body['Id'], url)
            if not isinstance(body["Devices"], list):
                errData += "Invalid simpleStorage Devices \"{}\" for {}, \n".format(
                    body['Devices'], url
                )
            return errData

        for node in ucsComputeList:
            url = "/redfish/v1/Systems/{}/SimpleStorage".format(node)
            api_data = fit_common.rackhdapi(url)
            if api_data['status'] != 200:
                errUrls += url + ' returned status ' + str(api_data['status']) + \
                    ', Expected 200,\n'
                continue
            for member in api_data['json']['Members']:
                _url = member['@odata.id']
                _api_data = fit_common.rackhdapi(_url)
                if _api_data['status'] != 200:
                    errUrls += _url + ' returned status ' + str(api_data['status']) + \
                        ', Expected 200,\n'
                _body = _api_data['json']
                errData = validate_simple_storage_data(_body, _url)
                if errData:
                    errUrls += errData
        self.assertEqual(len(errUrls), 0, errUrls)


if __name__ == '__main__':
    unittest.main()
