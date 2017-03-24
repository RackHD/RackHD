"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

"""
import fit_path  # NOQA: unused import                                                                                          
import unittest
import flogging

from config.redfish1_0_config import config
from on_http_redfish_1_0 import RedfishvApi as redfish
from on_http_redfish_1_0 import rest
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['redfish.managers.tests'], depends_on_groups=['redfish.systems.tests'])
@attr(regression=True, smoke=True, managers_rf1_tests=True)
class ManagersTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__managersList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.list_managers'])
    def test_list_managers(self):
        # """ Testing GET /Managers """
        redfish().list_managers()
        manager = self.__get_data()
        logs.debug(dumps(manager, indent=4))
        self.assertNotEqual(0, len(manager), msg='managers list was empty!')
        self.__class__.__managersList = manager.get('Members')
        self.assertIsNotNone(self.__class__.__managersList, msg='Manager members section was not found')
        self.assertNotEqual(len(self.__class__.__managersList), 0, msg='Manager members list is empty')

    # @test(groups=['redfish.get_manager'], depends_on_groups=['redfish.list_managers'])
    @depends(after='test_list_managers')
    def test_get_manager(self):
        # """ Testing GET /Managers/{identifier} """
        for member in self.__class__.__managersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            redfish().get_manager(dataId)
            manager = self.__get_data()
            logs.debug(dumps(manager, indent=4))
            id = manager.get('Id')
            self.assertEqual(dataId, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))

    # @test(groups=['redfish.get_manager_invalid'], depends_on_groups=['redfish.list_managers'])
    @depends(after='test_list_managers')
    def test_get_manager_invalid(self):
        # """ Testing GET /Managers/{identifier} 404s properly """
        for member in self.__class__.__managersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            try:
                redfish().get_manager(dataId + '1')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))

    # @test(groups=['redfish.list_manager_ethernet_interfaces'], depends_on_groups=['redfish.list_managers'])
    @depends(after='test_list_managers')
    def test_list_manager_ethernet_interfaces(self):
        # """ Testing GET /Managers/{identifier}/EthernetInterfaces """
        for member in self.__class__.__managersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            redfish().list_manager_ethernet_interfaces(dataId)
            interface = self.__get_data()
            logs.debug(dumps(interface, indent=4))
            count = interface.get('Members@odata.count')
            self.assertTrue(count >= 1, msg='expected count to be >= 1')

    # @test(groups=['redfish.list_manager_ethernet_interfaces_invalid'], depends_on_groups=['redfish.list_managers'])
    @depends(after='test_list_managers')
    def test_list_manager_ethernet_interfaces_invalid(self):
        # """ Testing GET /Managers/{identifier}/EthernetInterfaces 404s properly """
        for member in self.__class__.__managersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            try:
                redfish().list_manager_ethernet_interfaces(dataId + '1')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))

    # @test(groups=['redfish.get_manager_ethernet_interface'], depends_on_groups=['redfish.list_manager_ethernet_interfaces'])
    @depends(after='test_list_manager_ethernet_interfaces')
    def test_get_manager_ethernet_interface(self):
        # """ Testing GET /Managers/{identifier}/EthernetInterfaces/{id} """
        for member in self.__class__.__managersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            redfish().list_manager_ethernet_interfaces(dataId)
            managers = self.__get_data()
            for manager in managers.get('Members'):
                odata_id = manager.get('@odata.id')
                req_id = odata_id.split('/redfish/v1/Managers/' + dataId + '/EthernetInterfaces/')[1]
                redfish().get_manager_ethernet_interface(dataId, req_id)
                interface = self.__get_data()
                logs.debug(dumps(interface, indent=4))
                id = interface.get('Id')
                self.assertEqual(req_id, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))
                ipv4 = interface.get('IPv4Addresses')
                self.assertIsNotNone(ipv4)
                self.assertNotEqual(0, len(ipv4), msg='ipv4 list was empty!')
