from config.redfish1_0_config import *
from modules.logger import Log
from on_http_redfish_1_0 import RedfishvApi as redfish
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import loads,dumps

LOG = Log(__name__)

@test(groups=['redfish.task_service.tests'], \
      depends_on_groups=['redfish.systems.tests'])
class TaskServiceTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__oemServiceList = None
        self.__taskServiceList = None
        self.__taskList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['redfish.get_task_service_root'])
    def test_get_task_service_root(self):
        """ Testing GET /TaskService """
        redfish().task_service_root()
        taskService = self.__get_data()
        LOG.debug(taskService,json=True)
        self.__oemServiceList = taskService.get('Oem')
        assert_is_not_none(self.__oemServiceList)
        oemMembers = self.__oemServiceList['RackHD'] \
                                          ['SystemTaskCollection'].get('Members')
        assert_is_not_none(oemMembers)
        assert_not_equal(0, len(oemMembers), message='OEM members list was empty!')
        self.__taskServiceList = taskService.get('Tasks')
        assert_is_not_none(self.__taskServiceList)
        taskMembers = self.__taskServiceList.get('Members')
        assert_is_not_none(taskMembers)
        assert_not_equal(0, len(taskMembers), message='Task service members list was empty!')

    @test(groups=['redfish.get_list_tasks'], \
          depends_on_groups=['redfish.get_task_service_root'])
    def test_get_list_tasks(self):
        """ Testing GET /TaskService/Tasks """
        redfish().list_tasks()
        self.__taskList = self.__get_data()
        LOG.debug(self.__taskList,json=True)
        members = self.__taskList.get('Members')
        assert_is_not_none(members)
        assert_not_equal(0, len(members), message='Task members list was empty!')

    @test(groups=['redfish.get_task'], \
          depends_on_groups=['redfish.get_list_tasks'])
    def test_get_task(self):
        """ Testing GET /TaskService/Tasks/{identifier} """
        assert_is_not_none(self.__taskList)
        members = self.__taskList.get('Members')
        for member in members:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/TaskService/Tasks/')[1]
            redfish().get_task(dataId)
            task = self.__get_data()
            LOG.debug(task,json=True)
            taskId = task.get('@odata.id')
            taskId = taskId.split('/redfish/v1/TaskService/Tasks/')[1]
            assert_equal(dataId,taskId)

    @test(groups=['redfish.get_system_task'], \
          depends_on_groups=['redfish.get_list_tasks'])
    def test_get_system_task(self):
        """ Testing GET /TaskService/Oem/Tasks/{identifier} """
        assert_is_not_none(self.__oemServiceList)
        oemMembers = self.__oemServiceList['RackHD'] \
                                          ['SystemTaskCollection'].get('Members')
        for member in oemMembers:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/TaskService/Oem/Tasks/')[1]
            redfish().get_system_tasks(dataId)
            task = self.__get_data()
            LOG.debug(task,json=True)
            taskId = task.get('@odata.id')
            taskId = taskId.split('/redfish/v1/TaskService/Oem/Tasks/')[1]
            assert_equal(dataId,taskId)

