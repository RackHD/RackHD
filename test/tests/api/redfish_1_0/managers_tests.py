from config.redfish1_0_config import *
from modules.logger import Log
from on_http_redfish_1_0 import RedfishvApi as redfish
from on_http_redfish_1_0 import rest
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis.asserts import assert_is
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import loads,dumps
import re, time

LOG = Log(__name__)

@test(groups=['redfish.managers.tests'], depends_on_groups=['redfish.systems.tests'])
class ManagersTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__managersList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['redfish.list_managers'])
    def test_list_managers(self):
        """ Testing GET /Managers """
        redfish().list_managers()
        manager = self.__get_data()
        LOG.debug(manager,json=True)
        assert_not_equal(0, len(manager), message='managers list was empty!')
        self.__managersList = manager.get('Members')
        assert_is_not_none(self.__managersList)

    @test(groups=['redfish.get_manager'], depends_on_groups=['redfish.list_managers'])
    def test_get_manager(self):
        """ Testing GET /Managers/{identifier} """
        for member in self.__managersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            redfish().get_manager(dataId)
            manager = self.__get_data()
            LOG.debug(manager,json=True)
            id = manager.get('Id')
            assert_equal(dataId, id, message='unexpected id {0}, expected {1}'.format(id,dataId))

    @test(groups=['redfish.get_manager_invalid'], depends_on_groups=['redfish.list_managers'])
    def test_get_manager_invalid(self):
        """ Testing GET /Managers/{identifier} 404s properly """
        for member in self.__managersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            try:
                redfish().get_manager(dataId + '1')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))

    @test(groups=['redfish.list_manager_ethernet_interfaces'], depends_on_groups=['redfish.list_managers'])
    def test_list_manager_ethernet_interfaces(self):
        """ Testing GET /Managers/{identifier}/EthernetInterfaces """
        for member in self.__managersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            redfish().list_manager_ethernet_interfaces(dataId)
            interface = self.__get_data()
            LOG.debug(interface,json=True)
            count = interface.get('Members@odata.count')
            assert_true(count >= 1, message='expected count to be >= 1')

    @test(groups=['redfish.list_manager_ethernet_interfaces_invalid'], depends_on_groups=['redfish.list_managers'])
    def test_list_manager_ethernet_interfaces_invalid(self):
        """ Testing GET /Managers/{identifier}/EthernetInterfaces 404s properly """
        for member in self.__managersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            try:
                redfish().list_manager_ethernet_interfaces(dataId + '1')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))

    @test(groups=['redfish.get_manager_ethernet_interface'], depends_on_groups=['redfish.list_manager_ethernet_interfaces'])
    def test_get_manager_ethernet_interface(self):
        """ Testing GET /Managers/{identifier}/EthernetInterfaces/{id} """
        for member in self.__managersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Managers/')[1]
            redfish().list_manager_ethernet_interfaces(dataId)
            managers = self.__get_data();
            for manager in managers.get('Members'):
                odata_id = manager.get('@odata.id')
                req_id = odata_id.split('/redfish/v1/Managers/'+dataId+'/EthernetInterfaces/')[1]
                redfish().get_manager_ethernet_interface(dataId, req_id)
                interface = self.__get_data()
                LOG.debug(interface,json=True)
                id = interface.get('Id')
                assert_equal(req_id, id, message='unexpected id {0}, expected {1}'.format(id,dataId))
                ipv4 = interface.get('IPv4Addresses')
                assert_is_not_none(ipv4)
                assert_not_equal(0, len(ipv4), message='ipv4 list was empty!')

