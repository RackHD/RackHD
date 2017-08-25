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


@attr(regression=True, smoke=True, task_service_rf1_tests=True)
class TaskServiceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__oemServiceList = None
        cls.__taskServiceList = None
        cls.__taskList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.get_task_service_root'])
    def test_get_task_service_root(self):
        # """ Testing GET /TaskService """
        redfish().task_service_root()
        taskService = self.__get_data()
        logs.debug(dumps(taskService, indent=4))
        self.__class__.__oemServiceList = taskService.get('Oem')
        self.__oemServiceList = self.__class__.__oemServiceList
        self.assertIsNotNone(self.__oemServiceList)
        oemMembers = self.__oemServiceList['RackHD']['SystemTaskCollection'].get('Members')
        self.assertIsNotNone(oemMembers)
        self.assertNotEqual(0, len(oemMembers), msg='OEM members list was empty!')
        self.__class__.__taskServiceList = taskService.get('Tasks')
        self.__taskServiceList = self.__class__.__taskServiceList
        self.assertIsNotNone(self.__taskServiceList)

    # @test(groups=['redfish.get_list_tasks'], \
    #      depends_on_groups=['redfish.get_task_service_root'])
    @depends(after='test_get_task_service_root')
    def test_get_list_tasks(self):
        # """ Testing GET /TaskService/Tasks """
        redfish().list_tasks()
        self.__class__.__taskList = self.__get_data()
        self.__taskList = self.__class__.__taskList
        logs.debug(dumps(self.__taskList, indent=4))
        members = self.__taskList.get('Members')
        self.assertIsNotNone(members)
        self.assertNotEqual(0, len(members), msg='Task members list was empty!')

    # @test(groups=['redfish.get_task'], \
    #      depends_on_groups=['redfish.get_list_tasks'])
    @depends(after='test_get_list_tasks')
    def test_get_task(self):
        # """ Testing GET /TaskService/Tasks/{identifier} """
        self.__taskList = self.__class__.__taskList
        self.assertIsNotNone(self.__taskList)
        members = self.__taskList.get('Members')
        for member in members:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/TaskService/Tasks/')[1]
            redfish().get_task(dataId)
            task = self.__get_data()
            logs.debug(dumps(task, indent=4))
            taskId = task.get('@odata.id')
            taskId = taskId.split('/redfish/v1/TaskService/Tasks/')[1]
            self.assertEqual(dataId, taskId)

    # @test(groups=['redfish.get_system_task'], \
    #      depends_on_groups=['redfish.get_list_tasks'])
    @depends(after='test_get_list_tasks')
    def test_get_system_task(self):
        # """ Testing GET /TaskService/Oem/Tasks/{identifier} """
        self.__oemServiceList = self.__class__.__oemServiceList
        self.assertIsNotNone(self.__oemServiceList)
        oemMembers = self.__oemServiceList['RackHD']['SystemTaskCollection'].get('Members')
        for member in oemMembers:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/TaskService/Oem/Tasks/')[1]
            redfish().get_system_tasks(dataId)
            task = self.__get_data()
            logs.debug(dumps(task, indent=4))
            taskId = task.get('@odata.id')
            taskId = taskId.split('/redfish/v1/TaskService/Oem/Tasks/')[1]
            self.assertEqual(dataId, taskId)
