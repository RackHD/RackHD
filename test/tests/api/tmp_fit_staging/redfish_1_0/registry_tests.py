"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

"""
import fit_path  # NOQA: unused import                                                                                          
import unittest

from config.redfish1_0_config import config
from on_http_redfish_1_0 import RedfishvApi as redfish
from on_http_redfish_1_0 import rest
from json import loads, dumps
from nosedep import depends
import flogging
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['redfish.registry.tests'], depends_on_groups=['obm.tests'])
@attr(regression=True, smoke=True, registry_rf1_tests=True)
class RegistryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__registryList = None
        cls.__membersList = None
        cls.__locationUri = list()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.list_registry'])
    def test_list_registry(self):
        # """ Testing GET /Registries """
        redfish().list_registry()
        registry = self.__get_data()
        logs.debug(dumps(registry, indent=4))
        self.assertNotEqual(0, len(registry), msg='Registry list was empty!')
        self.__class__.__registryList = registry

    # @test(groups=['redfish.get_registry_file'], depends_on_groups=['redfish.list_registry'])
    @depends(after='test_list_registry')
    def test_get_registry_file(self):
        # """ Testing GET /Registries/{identifier} """
        self.__class__.__membersList = self.__class__.__registryList.get('Members')
        self.assertIsNotNone(self.__class__.__membersList, msg='Members section not present')
        self.assertNotEqual(len(self.__class__.__membersList), 0, msg='Members section is empty')
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/Registries/')[1]
            redfish().get_registry_file(dataId)
            registry_file = self.__get_data()
            logs.debug(dumps(registry_file, indent=4))
            id = registry_file.get('Id')
            self.assertEqual(dataId, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))
            self.assertEqual(type(registry_file.get('Location')), list, msg='expected list not found')
            location = registry_file.get('Location')[0]
            location_uri = location.get('Uri')
            # avoid python3 hound error by not using the word unicode
            self.assertEqual(type(location_uri),
                             type(u'unicode_string_type'),
                             msg='expected type for Uri not string-like, received {}'.format(location_uri))
            self.assertIn(dataId, location_uri, msg='expected dataId {} not in Uri {}'.format(dataId, location_uri))
            self.__class__.__locationUri.append(location.get('Uri'))

    # @test(groups=['redfish.get_registry_file_invalid'], depends_on_groups=['redfish.list_registry'])
    @depends(after='test_list_registry')
    def test_get_registry_file_invalid(self):
        # """ Testing GET /Registries/{identifier} 404s properly """
        self.__class__.__membersList = self.__class__.__registryList.get('Members')
        self.assertNotEqual(None, self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/Registries/')[1]
            try:
                redfish().get_registry_file(dataId + '-invalid')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))

    # @test(groups=['redfish.get_registry_file_contents'], depends_on_groups=['redfish.get_registry_file'])
    @depends(after='test_get_registry_file')
    def test_get_registry_file_contents(self):
        # """ Testing GET /Registries/en/{identifier} """
        self.assertNotEqual([], self.__class__.__locationUri)
        for member in self.__class__.__locationUri:
            self.assertNotEqual(None, member)
            dataId = member.split('/redfish/v1/Registries/en/')[1]
            redfish().get_registry_file_contents(dataId)
            registry_file_contents = self.__get_data()
            logs.debug(dumps(registry_file_contents, indent=4))
            id = registry_file_contents.get('Id')
            self.assertEqual(dataId, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))

    # @test(groups=['redfish.get_registry_file_contents_invalid'], depends_on_groups=['redfish.get_registry_file'])
    @depends(after='test_get_registry_file')
    def test_get_registry_file_contents_invalid(self):
        # """ Testing GET /Registries/en/{identifier} 404s properly """
        self.assertNotEqual([], self.__class__.__locationUri)
        for member in self.__class__.__locationUri:
            self.assertNotEqual(None, member)
            dataId = member.split('/redfish/v1/Registries/en/')[1]
            try:
                redfish().get_registry_file_contents(dataId + '-invalid')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))
