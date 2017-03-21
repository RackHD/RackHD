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
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import loads,dumps

LOG = Log(__name__)

@test(groups=['redfish.registry.tests'], depends_on_groups=['obm.tests'])
class RegistryTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__registryList = None
        self.__membersList = None
        self.__locationUri = []

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['redfish.list_registry'])
    def test_list_registry(self):
        """ Testing GET /Registries """
        redfish().list_registry()
        registry = self.__get_data()
        LOG.debug(registry,json=True)
        assert_not_equal(0, len(registry), message='Registry list was empty!')
        self.__registryList = registry

    @test(groups=['redfish.get_registry_file'], depends_on_groups=['redfish.list_registry'])
    def test_get_registry_file(self):
        """ Testing GET /Registries/{identifier} """
        self.__membersList = self.__registryList.get('Members')
        assert_not_equal(None, self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/Registries/')[1]
            redfish().get_registry_file(dataId)
            registry_file = self.__get_data()
            LOG.debug(registry_file,json=True)
            id = registry_file.get('Id')
            assert_equal(dataId, id, message='unexpected id {0}, expected {1}'.format(id,dataId))
            assert_equal(type(registry_file.get('Location')), list, message='expected list not found')
            location = registry_file.get('Location')[0]
            assert_equal(type(location.get('Uri')), unicode, message='expected uri string not found')
            self.__locationUri.append(location.get('Uri'))

    @test(groups=['redfish.get_registry_file_invalid'], depends_on_groups=['redfish.list_registry'])
    def test_get_registry_file_invalid(self):
        """ Testing GET /Registries/{identifier} 404s properly """
        self.__membersList = self.__registryList.get('Members')
        assert_not_equal(None, self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/Registries/')[1]
            try:
                redfish().get_registry_file(dataId + '-invalid')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))

    @test(groups=['redfish.get_registry_file_contents'], depends_on_groups=['redfish.get_registry_file'])
    def test_get_registry_file_contents(self):
        """ Testing GET /Registries/en/{identifier} """
        assert_not_equal([], self.__locationUri)
        for member in self.__locationUri:
            assert_not_equal(None,member)
            dataId = member.split('/redfish/v1/Registries/en/')[1]
            redfish().get_registry_file_contents(dataId)
            registry_file_contents = self.__get_data()
            LOG.debug(registry_file_contents,json=True)
            id = registry_file_contents.get('Id')
            assert_equal(dataId, id, message='unexpected id {0}, expected {1}'.format(id,dataId))

    @test(groups=['redfish.get_registry_file_contents_invalid'], depends_on_groups=['redfish.get_registry_file'])
    def test_get_registry_file_contents_invalid(self):
        """ Testing GET /Registries/en/{identifier} 404s properly """
        assert_not_equal([], self.__locationUri)
        for member in self.__locationUri:
            assert_not_equal(None,member)
            dataId = member.split('/redfish/v1/Registries/en/')[1]
            try:
                redfish().get_registry_file_contents(dataId + '-invalid')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))

