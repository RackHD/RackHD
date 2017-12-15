'''
Copyright 2017, Dell EMC, Inc.

Author(s):
    Krein Peng

UCS test script that tests:
- Redfish API for UCS nodes
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

    def validate_simple_storage_data(self, body, url):
        """
        Validate simple storage non-empty data body
        """
        errData = ''
        schema = {
            "str": ["Name", "Id", "Description"],
            "list": ["Devices"]
        }
        errStr = ucs_common.validate_redfish_data_payload(body, schema, url)
        if errStr:
            errData += errStr
        if not re.compile('^\w{0,}_\w{1,3}_\w{1,}_\w{1}$').match(body['Id']):
            errData += "Invalid simpleStorage Id \"{}\" for {}, \n".format(body['Id'], url)
        return errData

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
        initialNodeCount = len(ucs_common.get_ucs_node_list())
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

        newNodeCount = len(ucs_common.get_ucs_node_list())
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
        ucsEnclList = ucs_common.get_ucs_encl_id_list()
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
                _body = api_data['json']
                schema = {
                    "str": ["Name", "ChassisType", "Manufacturer", "Model",
                            "SerialNumber", "IndicatorLED"],
                    "dict": ["Thermal", "Power", "Links"]
                }
                errData = ucs_common.validate_redfish_data_payload(_body, schema, url)
                if errData:
                    errUrls += errData
        self.assertEqual(len(ucsEnclList), 0, 'not all UCS chassis were listed under /chassis')
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_redfish_chassis])
    @unittest.skip("Skipping 'test_api_redfish_chassis_thermal' which is not ready")
    def test_api_redfish_chassis_thermal(self):
        """
        Tests the redfish /Chassis/{identifier}/Thermal APIs with UCS nodes
        :return:
        """
        ucsEnclList = ucs_common.get_ucs_encl_id_list()
        errUrls = ''
        for chassis in ucsEnclList:
            url = '/redfish/v1/Chassis/{}/Thermal'.format(chassis)
            api_data = fit_common.rackhdapi(url)
            if api_data['status'] != 200:
                errUrls += url + ' returned status ' + str(api_data['status']) + ',\n'
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_redfish_chassis])
    @unittest.skip("Skipping 'test_api_redfish_chassis_power' which is not ready")
    def test_api_redfish_chassis_power(self):
        """
        Tests the redfish /Chassis/{identifier}/Power APIs with UCS nodes
        :return:
        """
        ucsEnclList = ucs_common.get_ucs_encl_id_list()
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
        ucsComputeList = ucs_common.get_ucs_compute_id_list()
        errUrls = ''

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
                schema = {
                    "str": ["Name", "SystemType", "Manufacturer", "Model", "SerialNumber",
                            "IndicatorLED", "PowerState", "BiosVersion"],
                    "dict": ["ProcessorSummary", "MemorySummary", "Actions", "Processors",
                             "EthernetInterfaces", "SimpleStorage", "LogServices",
                             "Links", "Storage"]
                }
                errData = ucs_common.validate_redfish_data_payload(_body, schema, url)
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
        ucsComputeList = ucs_common.get_ucs_compute_id_list()
        errUrls = ''

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
            for member in api_data['json']['Members']:
                _url = member['@odata.id']
                _api_data = fit_common.rackhdapi(_url)
                if _api_data['status'] != 200:
                    errUrls += _url + ' returned status ' + str(api_data['status']) + \
                        ', Expected 200,\n'
                _body = _api_data['json']
                schema = {
                    "str": ["Socket", "ProcessorType", "ProcessorArchitecture",
                            "InstructionSet", "Manufacturer", "Model"],
                    "int": ["MaxSpeedMHz", "TotalCores", "TotalThreads"]
                }
                errData = ucs_common.validate_redfish_data_payload(_body, schema, url)
                if errData:
                    errUrls += errData
        self.assertEqual(len(errUrls), 0, errUrls)

    @depends(after=[test_api_redfish_system])
    @unittest.skip("Skipping 'test_api_redfish_simple_storage' which is not ready")
    def test_api_redfish_simple_storage(self):
        """
        Tests the redfish /Systems/{identifier}/simpleStorage APIs with UCS nodes
        :return:
        """
        ucsComputeList = ucs_common.get_ucs_compute_id_list()
        errUrls = ''

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
                errData = self.validate_simple_storage_data(_body, _url)
                if errData:
                    errUrls += errData
        self.assertEqual(len(errUrls), 0, errUrls)


if __name__ == '__main__':
    unittest.main()
