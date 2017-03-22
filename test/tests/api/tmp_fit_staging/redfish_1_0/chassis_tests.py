"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import fit_path  # NOQA: unused import                                                                                          
import unittest
import flogging

from config.redfish1_0_config import config
from on_http_redfish_1_0 import RedfishvApi as redfish
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['redfish.chassis.tests'],
#    depends_on_groups=['obm.tests', 'amqp.tests'])
@attr(regression=True, smoke=True, chassis_rf1_tests=True)
class ChassisTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__chassisList = None
        cls.__membersList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.list_chassis'])
    def test_list_chassis(self):
        # """ Testing GET /Chassis """
        redfish().list_chassis()
        chassis = self.__get_data()
        logs.debug(dumps(chassis, indent=4))
        self.assertNotEqual(0, len(chassis), msg='Chassis list was empty!')
        self.__class__.__chassisList = chassis

    # @test(groups=['redfish.get_chassis'], depends_on_groups=['redfish.list_chassis'])
    @depends(after='test_list_chassis')
    def test_get_chassis(self):
        # """ Testing GET /Chassis/{identifier} """
        self.__class__.__membersList = self.__class__.__chassisList.get('Members')
        self.assertNotEqual(None, self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/Chassis/')[1]
            logs.info("Chassis: %s", dataId)
            redfish().get_chassis(dataId)
            chassis = self.__get_data()
            logs.debug(dumps(chassis, indent=4))
            id = chassis.get('Id')
            self.assertEqual(dataId, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))
            member['ChassisType'] = chassis.get('ChassisType')
            member['Id'] = id

    # @test(groups=['redfish.get_chassis_thermal'], depends_on_groups=['redfish.get_chassis'])
    @depends(after='test_get_chassis')
    def test_get_chassis_thermal(self):
        # """ Testing GET /Chassis/{identifier}/Thermal """
        for member in self.__class__.__membersList:
            logs.info("Chassis:  %s", member.get('Id'))
            redfish().get_thermal(member.get('Id'))
            thermal = self.__get_data()
            logs.debug(dumps(thermal, indent=4))
            self.assertNotEqual({}, thermal, msg='thermal object undefined!')
            name = thermal.get('Name')
            self.assertNotEqual('', name, msg='empty thermal name!')
            temperature = thermal.get('Temperatures')
            self.assertNotEqual(0, len(temperature), msg='temperature list was empty!')
            if member.get('ChassisType') == 'Enclosure':
                fans = thermal.get('Fans')
                self.assertNotEqual(0, len(fans), msg='fans list was empty!')

    # @test(groups=['redfish.get_chassis_power'], depends_on_groups=['redfish.get_chassis'])
    @depends(after='test_get_chassis')
    def test_get_chassis_power(self):
        # """ Testing GET /Chassis/{identifier}/Power """
        for member in self.__class__.__membersList:
            logs.info("Chassis:  %s", member.get('Id'))
            redfish().get_power(member.get('Id'))
            power = self.__get_data()
            logs.debug(dumps(power, indent=4))
            self.assertNotEqual({}, power, msg='power object undefined!')
            name = power.get('Name')
            self.assertNotEqual('', name, msg='empty power name!')
            if member.get('ChassisType') != 'Enclosure':
                voltages = power.get('Voltages')
                self.assertNotEqual(0, len(voltages), msg='voltages list was empty!')
