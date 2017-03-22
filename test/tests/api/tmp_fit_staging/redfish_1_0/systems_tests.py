"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

"""
import fit_path  # NOQA: unused import                                                                                          
import unittest
import flogging
import re
import time

from config.redfish1_0_config import config
from on_http_redfish_1_0 import RedfishvApi as redfish
from on_http_redfish_1_0 import rest
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['redfish.systems.tests'], depends_on_groups=['redfish.chassis.tests'])
@attr(regression=True, smoke=True, system_rf1_tests=True)
class SystemsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__systemsList = None
        cls.__membersList = None
        cls.__systemProcessorsList = None
        cls.__simpleStorageList = None
        cls.__logServicesList = None
        cls.__resetActionTypes = None
        cls.__bootImageTypes = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.list_systems'])
    def test_list_systems(self):
        # """ Testing GET /Systems """
        redfish().list_systems()
        self.__class__.__systemsList = self.__get_data()
        logs.debug(dumps(self.__class__.__systemsList, indent=4))
        self.assertNotEqual(0, len(self.__class__.__systemsList), msg='systems list was empty!')

    # @test(groups=['redfish.get_systems'],\
    #        depends_on_groups=['redfish.list_systems'])
    @depends(after='test_list_systems')
    def test_get_systems(self):
        # """ Testing GET /Systems/{identifier} """
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().get_system(dataId)
            systems = self.__get_data()
            logs.debug(dumps(systems, indent=4))
            id = systems.get('Id')
            self.assertEqual(dataId, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))

    # @test(groups=['redfish.list_system_processors'],\
    #        depends_on_groups=['redfish.get_systems'])
    @depends(after='test_get_systems')
    def test_list_system_processors(self):
        # """ Testing GET /Systems/{identifier}/Processors """
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_system_processors(dataId)
            self.__class__.__systemProcessorsList = self.__get_data()
            logs.debug(dumps(self.__class__.__systemProcessorsList, indent=4))
            membersList = self.__class__.__systemProcessorsList.get('Members')
            self.assertIsNotNone(membersList, msg='missing processor members field!')
            count = self.__class__.__systemProcessorsList.get('Members@odata.count')
            self.assertIsNotNone(count, msg='missing processor member count field!')
            self.assertEqual(count, len(membersList))

    # @test(groups=['redfish.get_system_processor'],\
    #        depends_on_groups=['redfish.list_system_processors'])
    @depends(after='test_list_system_processors')
    def test_get_system_processor(self):
        # """ Testing GET /Systems/{identifier}/Processors/{socket} """
        self.assertIsNotNone(self.__class__.__membersList)
        membersList = self.__class__.__systemProcessorsList.get('Members')
        self.assertIsNotNone(membersList, msg='missing processor members field!')
        socket = 0
        for member in membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            id = re.compile(r'/Processors/[0-9]+').split(dataId)[0].split('/redfish/v1/Systems/')[1]
            redfish().get_system_processor(id, socket)
            processor = self.__get_data()
            logs.debug(dumps(processor, indent=4))
            procId = processor.get('@odata.id')
            self.assertEqual(dataId, procId)
            socket += 1

    # @test(groups=['redfish.list_system_simplestorage'],\
    #        depends_on_groups=['redfish.get_systems'])
    @depends(after='test_get_systems')
    def test_list_simple_storage(self):
        # """ Testing GET /Systems/{identifier}/SimpleStorage """
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_simple_storage(dataId)
            self.__class__.__simpleStorageList = self.__get_data()
            logs.debug(dumps(self.__class__.__simpleStorageList, indent=4))
            membersList = self.__class__.__simpleStorageList.get('Members')
            self.assertIsNotNone(membersList, msg='missing simplestorage members field!')
            count = self.__class__.__simpleStorageList.get('Members@odata.count')
            self.assertIsNotNone(count, msg='missing simple storage member count field!')
            self.assertEqual(count, len(membersList))

    # @test(groups=['redfish.get_system_simplestorage'],\
    #      depends_on_groups=['redfish.list_system_simplestorage'])
    @depends(after='test_list_simple_storage')
    def test_get_simple_storage(self):
        # """ Testing GET /Systems/{identifier}/SimpleStorage/{index} """
        self.assertIsNotNone(self.__class__.__membersList)
        membersList = self.__class__.__simpleStorageList.get('Members')
        self.assertIsNotNone(membersList, msg='missing simple storage members field!')
        for member in membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            index = dataId.split('/SimpleStorage/')[1]
            id = re.compile(r'/SimpleStorage/[0-9]+').split(dataId)[0].split('/redfish/v1/Systems/')[1]
            redfish().get_simple_storage(id, index)
            storage = self.__get_data()
            logs.debug(dumps(storage, indent=4))
            storageId = storage.get('@odata.id')
            self.assertEqual(dataId, storageId)

    # @test(groups=['redfish.list_system_log_services'],\
    #        depends_on_groups=['redfish.get_systems'])
    @depends(after='test_get_systems')
    def test_list_log_services(self):
        # """ Testing GET /Systems/{identifier}/LogServices """
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_log_service(dataId)
            self.__class__.__logServicesList = self.__get_data()
            logs.debug(dumps(self.__class__.__logServicesList, indent=4))
            membersList = self.__class__.__logServicesList.get('Members')
            self.assertIsNotNone(membersList, msg='missing logservices members field!')
            count = self.__class__.__logServicesList.get('Members@odata.count')
            self.assertIsNotNone(count, msg='missing logservices member count field!')
            self.assertEqual(count, len(membersList))

    # @test(groups=['redfish.get_sel_log_service'],\
    #        depends_on_groups=['redfish.list_system_log_services'])
    @depends(after='test_list_log_services')
    def test_get_sel_log_services(self):
        # """ Testing GET /Systems/{identifier}/LogServices/sel """
        self.assertIsNotNone(self.__class__.__membersList)
        membersList = self.__class__.__logServicesList.get('Members')
        self.assertIsNotNone(membersList, msg='missing log services members field!')
        for member in membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            id = re.compile(r'/LogServices').split(dataId)[0].split('/redfish/v1/Systems/')[1]
            logs.info("System ID: %s ", id)
            redfish().get_sel_log_service(id)
            sel = self.__get_data()
            logs.debug(dumps(sel, indent=4))
            selId = sel.get('@odata.id')
            self.assertEqual(dataId, selId)

    # @test(groups=['redfish.get_sel_log_service_entries'],\
    #        depends_on_groups=['redfish.list_system_log_services'])
    @depends(after='test_list_log_services')
    def test_get_sel_log_services_entries(self):
        # """ Testing GET /Systems/{identifier}/LogServices/sel/Entries """
        self.assertIsNotNone(self.__class__.__membersList)
        membersList = self.__class__.__logServicesList.get('Members')
        self.assertIsNotNone(membersList, msg='missing log services members field!')
        for member in membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            id = re.compile(r'/LogServices').split(dataId)[0].split('/redfish/v1/Systems/')[1]
            logs.info("System ID: %s ", id)
            redfish().list_sel_log_service_entries(id)
            entries = self.__get_data()
            self.assertNotEqual({}, entries)
            # Should validate the SEL entries here
            # Leaving as TODO until a 'add_sel' task is available
            logs.debug(dumps(entries, indent=4))

    # @test(groups=['redfish.get_sel_log_service_entries_entryid'],\
    #        depends_on_groups=['redfish.get_sel_log_service_entries'])
    @depends(after='test_get_sel_log_services_entries')
    def test_get_sel_log_services_entries_entryid(self):
        # """ Testing GET /Systems/{identifier}/LogServices/sel/Entries/{entryId} """
        # TODO Add more validation when a 'add_sel' task is available
        self.assertIsNotNone(self.__class__.__membersList)
        membersList = self.__class__.__logServicesList.get('Members')
        self.assertIsNotNone(membersList, msg='missing log services members field!')

    # @test(groups=['redfish.get_systems_actions_reset'],\
    #        depends_on_groups=['redfish.get_systems'])
    @depends(after='test_get_systems')
    def test_get_systems_actions_reset(self):
        # """ Testing GET /Systems/{identifier}/Actions/ComputerSystem.Reset """
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            logs.info("System ID: %s ", dataId)
            redfish().list_reset_types(dataId)
            reset_actions = self.__get_data()
            logs.debug(dumps(reset_actions, indent=4))
            self.__class__.__resetActionTypes = reset_actions.get('reset_type@Redfish.AllowableValues')
            self.assertEqual(dumps(self.__class__.__resetActionTypes), dumps(['On',
                                                                              'ForceOff',
                                                                              'GracefulRestart',
                                                                              'ForceRestart',
                                                                              'ForceOn',
                                                                              'PushPowerButton']))

    # @test(groups=['redfish.post_systems_actions_reset'],\
    #        depends_on_groups=['redfish.get_systems_actions_reset'])
    @depends(after='test_get_systems_actions_reset')
    def test_post_systems_actions_reset(self):
        # """ Testing POST /Systems/{identifier}/Actions/ComputerSystem.Reset """
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        self.assertIsNotNone(self.__class__.__resetActionTypes)
        for member in self.__class__.__membersList:
            actionsCompleted = 0
            dataId = member.get('@odata.id')
            self.assertNotEqual(0, len(dataId))
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            logs.info("System ID: %s ", dataId)
            for action in self.__class__.__resetActionTypes:
                if action == 'PushPowerButton':     # skip manual test
                    logs.warning('skipping "PushPowerButton" reset action')
                    continue
                logs.info('testing reset action "%s" for %s', action, dataId)
                try:
                    redfish().do_reset(dataId, {'reset_type': action})
                except rest.ApiException as err:
                    message = loads(err.body)['message']
                    if message == 'value not found in map':
                        logs.warning('%s for "%s", skipping..', message, action)
                        continue
                    else:
                        raise(err)
                task = self.__get_data()
                taskId = task.get('@odata.id')
                self.assertIsNotNone(taskId)
                taskId = taskId.split('/redfish/v1/TaskService/Tasks/')[1]
                timeout = 20
                while timeout > 0:
                    redfish().get_task(taskId)
                    taskInfo = self.__get_data()
                    taskState = taskInfo.get('TaskState')
                    taskStatus = taskInfo.get('TaskStatus')
                    self.assertIsNotNone(taskState)
                    self.assertIsNotNone(taskStatus)
                    if taskState == "Completed" and taskStatus == "OK":
                        actionsCompleted += 1
                        break
                    logs.warning('waiting for reset action %s (state=%s, status=%s)',
                                 action, taskState, taskStatus)
                    timeout -= 1
                    time.sleep(2)
                if timeout == 0:
                    self.fail('timed out waiting for reset action {0}'.format(action))
            if actionsCompleted == 0:
                self.fail('no reset actions were completed for id {0}'.format(dataId))

    # @test(groups=['redfish.get_systems_actions_bootimage'],\
    #        depends_on_groups=['redfish.get_systems'])
    @depends(after='test_get_systems')
    def test_get_systems_actions_bootimage(self):
        # """ Testing GET /Systems/{identifier}/Actions/RackHD.BootImage """
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertIsNotNone(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            logs.info("System ID: %s ", dataId)
            redfish().list_boot_image(dataId)
            bootImages = self.__get_data()
            logs.debug(dumps(bootImages, indent=4))
            self.__class__.__bootImageTypes = bootImages.get('osNames@Redfish.AllowableValues')
            self.assertIsNotNone(self.__class__.__bootImageTypes)
            self.assertEqual(dumps(self.__class__.__bootImageTypes), dumps(['CentOS',
                                                                            'CentOS+KVM',
                                                                            'ESXi',
                                                                            'RHEL',
                                                                            'RHEL+KVM']))

    # @test(groups=['redfish.post_systems_actions_bootimage'],\
    #        depends_on_groups=['redfish.get_systems_actions_bootimage'])
    @depends(after='test_get_systems_actions_bootimage')
    def test_post_systems_actions_bootimage(self):
        # """ Testing POST /Systems/{identifier}/Actions/RackHD.BootImage """
        # TODO run some OS installer workflows
        self.__class__.__membersList = self.__class__.__systemsList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList)
        self.assertIsNotNone(self.__class__.__bootImageTypes)
