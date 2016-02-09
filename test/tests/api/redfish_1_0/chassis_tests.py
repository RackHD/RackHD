from config.redfish1_0_config import *
from modules.logger import Log
from on_http_redfish_1_0 import RedfishvApi as redfish
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import loads,dumps

LOG = Log(__name__)

@test(groups=['redfish.chassis.tests'], depends_on_groups=['obm.tests'])
class ChassisTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__chassisList = None
        self.__membersList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['redfish.list_chassis'])
    def test_list_chassis(self):
        """ Testing GET /Chassis """
        redfish().list_chassis()
        chassis = self.__get_data()
        LOG.debug(chassis,json=True)
        assert_not_equal(0, len(chassis), message='Chassis list was empty!')
        self.__chassisList = chassis
    
    @test(groups=['redfish.get_chassis'], depends_on_groups=['redfish.list_chassis'])
    def test_get_chassis(self):
        """ Testing GET /Chassis/{identifier} """
        self.__membersList = self.__chassisList.get('Members')
        assert_not_equal(None, self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/Chassis/')[1]
            LOG.info(dataId)
            redfish().get_chassis(dataId)
            chassis = self.__get_data()
            LOG.debug(chassis,json=True)
            id = chassis.get('Id')
            assert_equal(dataId, id, message='unexpected id {0}, expected {1}'.format(id,dataId))

    @test(groups=['redfish.get_chassis_thermal'], depends_on_groups=['redfish.get_chassis'])
    def test_get_chassis_thermal(self):
        """ Testing GET /Chassis/{identifier}/Thermal """
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/Chassis/')[1]
            redfish().get_thermal(dataId)
            thermal = self.__get_data()
            LOG.debug(thermal,json=True)
            assert_not_equal({}, thermal, message='thermal object undefined!')
            name = thermal.get('Name')
            assert_not_equal('', name, message='empty thermal name!')
            temperature = thermal.get('Temperatures')
            assert_not_equal(0, len(temperature), message='temperature list was empty!')
            fans = thermal.get('Fans')
            assert_not_equal(0, len(fans), message='fans list was empty!')
            
            
    @test(groups=['redfish.get_chassis_power'], depends_on_groups=['redfish.get_chassis'])
    def test_get_chassis_power(self):
        """ Testing GET /Chassis/{identifier}/Power """
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/Chassis/')[1]
            redfish().get_power(dataId)
            power = self.__get_data()
            LOG.debug(power,json=True)
            assert_not_equal({}, power, message='power object undefined!')
            name = power.get('Name')
            assert_not_equal('', name, message='empty power name!')
            voltages = power.get('Voltages')
            assert_not_equal(0, len(power), message='voltages list was empty!')
            
