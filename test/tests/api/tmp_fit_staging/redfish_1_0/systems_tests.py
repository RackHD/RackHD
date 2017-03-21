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

@test(groups=['redfish.systems.tests'], depends_on_groups=['redfish.chassis.tests'])
class SystemsTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__systemsList = None
        self.__membersList = None
        self.__systemProcessorsList = None
        self.__simpleStorageList = None
        self.__logServicesList = None
        self.__resetActionTypes = None
        self.__bootImageTypes = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['redfish.list_systems'])
    def test_list_systems(self):
        """ Testing GET /Systems """
        redfish().list_systems()
        self.__systemsList = self.__get_data()
        LOG.debug(self.__systemsList,json=True)
        assert_not_equal(0, len(self.__systemsList), message='systems list was empty!')
        
    @test(groups=['redfish.get_systems'],\
            depends_on_groups=['redfish.list_systems'])
    def test_get_systems(self):
        """ Testing GET /Systems/{identifier} """
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none(self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().get_system(dataId)
            systems = self.__get_data()
            LOG.debug(systems,json=True)
            id = systems.get('Id')
            assert_equal(dataId, id, message='unexpected id {0}, expected {1}'.format(id,dataId))

    @test(groups=['redfish.list_system_processors'],\
            depends_on_groups=['redfish.get_systems'])
    def test_list_system_processors(self):
        """ Testing GET /Systems/{identifier}/Processors """
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none(self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_system_processors(dataId)
            self.__systemProcessorsList = self.__get_data()
            LOG.debug(self.__systemProcessorsList,json=True)
            membersList = self.__systemProcessorsList.get('Members')
            assert_is_not_none(membersList, message='missing processor members field!')
            count = self.__systemProcessorsList.get('Members@odata.count')
            assert_is_not_none(count, message='missing processor member count field!')
            assert_equal(count,len(membersList))

    @test(groups=['redfish.get_system_processor'],\
            depends_on_groups=['redfish.list_system_processors'])
    def test_get_system_processor(self):
        """ Testing GET /Systems/{identifier}/Processors/{socket} """
        assert_is_not_none(self.__membersList)
        membersList = self.__systemProcessorsList.get('Members')
        assert_is_not_none(membersList, message='missing processor members field!')
        socket = 0
        for member in membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            id = re.compile(r'/Processors/[0-9]+').split(dataId)[0]\
                    .split('/redfish/v1/Systems/')[1]
            redfish().get_system_processor(id, socket)
            processor = self.__get_data()
            LOG.debug(processor,json=True)
            procId = processor.get('@odata.id')
            assert_equal(dataId,procId)
            socket = socket + 1

    @test(groups=['redfish.list_system_simplestorage'],\
            depends_on_groups=['redfish.get_systems'])
    def test_list_simple_storage(self):
        """ Testing GET /Systems/{identifier}/SimpleStorage """
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none(self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_simple_storage(dataId)
            self.__simpleStorageList = self.__get_data()
            LOG.debug(self.__simpleStorageList,json=True)
            membersList = self.__simpleStorageList.get('Members')
            assert_is_not_none(membersList, message='missing simplestorage members field!')
            count = self.__simpleStorageList.get('Members@odata.count')
            assert_is_not_none(count, message='missing simple storage member count field!')
            assert_equal(count,len(membersList))

    @test(groups=['redfish.get_system_simplestorage'],\
            depends_on_groups=['redfish.list_system_simplestorage'])
    def test_get_simple_storage(self):
        """ Testing GET /Systems/{identifier}/SimpleStorage/{index} """
        assert_is_not_none(self.__membersList)
        membersList = self.__simpleStorageList.get('Members')
        assert_is_not_none(membersList, message='missing simple storage members field!')
        for member in membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            index = dataId.split('/SimpleStorage/')[1]
            id = re.compile(r'/SimpleStorage/[0-9]+').split(dataId)[0]\
                    .split('/redfish/v1/Systems/')[1]
            redfish().get_simple_storage(id, index)
            storage = self.__get_data()
            LOG.debug(storage,json=True)
            storageId = storage.get('@odata.id')
            assert_equal(dataId,storageId)

    @test(groups=['redfish.list_system_log_services'],\
            depends_on_groups=['redfish.get_systems'])
    def test_list_log_servives(self):
        """ Testing GET /Systems/{identifier}/LogServices """
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none(self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_log_service(dataId)
            self.__logServicesList = self.__get_data()
            LOG.debug(self.__logServicesList,json=True)
            membersList = self.__logServicesList.get('Members')
            assert_is_not_none(membersList, message='missing logservices members field!')
            count = self.__logServicesList.get('Members@odata.count')
            assert_is_not_none(count, message='missing logservices member count field!')
            assert_equal(count,len(membersList))

    @test(groups=['redfish.get_sel_log_service'],\
            depends_on_groups=['redfish.list_system_log_services'])
    def test_get_sel_log_services(self):
        """ Testing GET /Systems/{identifier}/LogServices/sel """
        assert_is_not_none(self.__membersList)
        membersList = self.__logServicesList.get('Members')
        assert_is_not_none(membersList, message='missing log services members field!')
        for member in membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            id = re.compile(r'/LogServices').split(dataId)[0]\
                    .split('/redfish/v1/Systems/')[1]
            redfish().get_sel_log_service(id)
            sel = self.__get_data()
            LOG.debug(sel,json=True)
            selId = sel.get('@odata.id')
            assert_equal(dataId,selId)

    @test(groups=['redfish.get_sel_log_service_entries'],\
            depends_on_groups=['redfish.list_system_log_services'])
    def test_get_sel_log_services_entries(self):
        """ Testing GET /Systems/{identifier}/LogServices/sel/Entries """
        assert_is_not_none( self.__membersList)
        membersList = self.__logServicesList.get('Members')
        assert_is_not_none(membersList, message='missing log services members field!')
        for member in membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            id = re.compile(r'/LogServices').split(dataId)[0]\
                    .split('/redfish/v1/Systems/')[1]
            redfish().list_sel_log_service_entries(id)
            entries = self.__get_data()
            assert_not_equal({},entries)
            # Should validate the SEL entries here
            # Leaving as TODO until a 'add_sel' task is available
            LOG.debug(entries,json=True)


    @test(groups=['redfish.get_sel_log_service_entries_entryid'],\
            depends_on_groups=['redfish.get_sel_log_service_entries'])
    def test_get_sel_log_services_entries_entryid(self):
        """ Testing GET /Systems/{identifier}/LogServices/sel/Entries/{entryId} """
        # TODO Add more validation when a 'add_sel' task is available
        assert_is_not_none( self.__membersList)
        membersList = self.__logServicesList.get('Members')
        assert_is_not_none(membersList, message='missing log services members field!')

    @test(groups=['redfish.get_systems_actions_reset'],\
            depends_on_groups=['redfish.get_systems'])
    def test_get_systems_actions_reset(self):
        """ Testing GET /Systems/{identifier}/Actions/ComputerSystem.Reset """
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none( self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_reset_types(dataId)
            reset_actions = self.__get_data()
            LOG.debug(reset_actions,json=True)
            self.__resetActionTypes = reset_actions.get('reset_type@Redfish.AllowableValues')
            assert_equal(dumps(self.__resetActionTypes), dumps(['On',\
                                                                'ForceOff',\
                                                                'GracefulRestart',\
                                                                'ForceRestart',\
                                                                'ForceOn',\
                                                                'PushPowerButton']))

    # @test(groups=['redfish.post_systems_actions_reset'],\
    #        depends_on_groups=['redfish.get_systems_actions_reset'])
    def test_post_systems_actions_reset(self):
        """ Testing POST /Systems/{identifier}/Actions/ComputerSystem.Reset """
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none(self.__membersList)
        assert_is_not_none(self.__resetActionTypes)
        for member in self.__membersList:
            actionsCompleted = 0
            dataId = member.get('@odata.id')
            assert_not_equal(0,len(dataId))
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            for action in self.__resetActionTypes:
                if action == 'PushPowerButton': # skip manual test
                    LOG.warning('skipping \"PushPowerButton\" reset action')
                    continue
                LOG.info('testing reset action {0}'.format(action))
                try:
                    redfish().do_reset(dataId,{'reset_type': action})
                except rest.ApiException as err:
                    message = loads(err.body)['message']
                    if message == 'value not found in map':
                        LOG.warning('{0} for \"{1}\", skipping..'.format(message,action))
                        continue
                    else:
                        raise(err)
                task = self.__get_data()
                taskId = task.get('@odata.id')
                assert_is_not_none(taskId)
                taskId = taskId.split('/redfish/v1/TaskService/Tasks/')[1]
                timeout = 20
                while timeout > 0:
                    redfish().get_task(taskId)
                    taskInfo = self.__get_data()
                    taskState = taskInfo.get('TaskState')
                    taskStatus = taskInfo.get('TaskStatus')
                    assert_is_not_none(taskState)
                    assert_is_not_none(taskStatus)
                    if taskState == "Completed" and \
                       taskStatus == "OK":
                        actionsCompleted += 1
                        break
                    LOG.warning('waiting for reset action {0} (state={1},status={2})' \
                            .format(action, taskState, taskStatus))
                    timeout -= 1
                    time.sleep(1)
                if timeout == 0:
                    fail('timed out waiting for reset action {0}'.format(action))
            if actionsCompleted == 0:
                fail('no reset actions were completed for id {0}'.format(dataId))

    @test(groups=['redfish.get_systems_actions_bootimage'],\
            depends_on_groups=['redfish.get_systems'])
    def test_get_systems_actions_bootimage(self):
        """ Testing GET /Systems/{identifier}/Actions/RackHD.BootImage """
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none(self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_is_not_none(dataId)
            dataId = dataId.split('/redfish/v1/Systems/')[1]
            redfish().list_boot_image(dataId)
            bootImages = self.__get_data()
            LOG.debug(bootImages,json=True)
            self.__bootImageTypes = bootImages.get('osNames@Redfish.AllowableValues')
            assert_is_not_none(self.__bootImageTypes)
            assert_equal(dumps(self.__bootImageTypes), dumps(['CentOS',\
                                                              'CentOS+KVM',\
                                                              'ESXi',\
                                                              'RHEL',\
                                                              'RHEL+KVM']))

    @test(groups=['redfish.post_systems_actions_bootimage'],\
            depends_on_groups=['redfish.get_systems_actions_bootimage'])
    def test_post_systems_actions_bootimage(self):
        """ Testing POST /Systems/{identifier}/Actions/RackHD.BootImage """
        # TODO run some OS installer workflows
        self.__membersList = self.__systemsList.get('Members')
        assert_is_not_none(self.__membersList)
        assert_is_not_none(self.__bootImageTypes)

