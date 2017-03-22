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


# @test(groups=['redfish.schema.tests'], depends_on_groups=['obm.tests'])
@attr(regression=True, smoke=True, schema_rf1_tests=True)
class SchemaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__schemaList = None
        cls.__membersList = None
        cls.__locationUri = []

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.list_schemas'])
    def test_list_schemas(self):
        # """ Testing GET /Schemas """
        redfish().list_schemas()
        schemas = self.__get_data()
        logs.debug(dumps(schemas, indent=4))
        self.assertNotEqual(0, len(schemas), msg='Schema list was empty!')
        self.__class__.__schemaList = schemas

    # @test(groups=['redfish.get_schema'], depends_on_groups=['redfish.list_schemas'])
    @depends(after='test_list_schemas')
    def test_get_schema(self):
        # """ Testing GET /Schemas/{identifier} """
        self.__class__.__membersList = self.__class__.__schemaList.get('Members')
        self.assertNotEqual(None, self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/Schemas/')[1]
            redfish().get_schema(dataId)
            schema_ref = self.__get_data()
            logs.debug(dumps(schema_ref, indent=4))
            id = schema_ref.get('Id')
            self.assertEqual(dataId, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))
            self.assertEqual(type(schema_ref.get('Location')), list, msg='expected list not found')
            location = schema_ref.get('Location')[0]
            self.assertEqual(type(location.get('Uri')), unicode, msg='expected uri string not found')
            self.__class__.__locationUri.append(location.get('Uri'))

    # @test(groups=['redfish.get_schema_invalid'], depends_on_groups=['redfish.list_schemas'])
    @depends(after='test_list_schemas')
    def test_get_schema_invalid(self):
        # """ Testing GET /Schemas/{identifier} 404s properly """
        self.__class__.__membersList = self.__class__.__schemaList.get('Members')
        self.assertNotEqual(None, self.__class__.__membersList)
        for member in self.__class__.__membersList:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/Schemas/')[1]
            try:
                redfish().get_schema(dataId + '-invalid')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))
            break

    # @test(groups=['redfish.get_schema_content'], depends_on_groups=['redfish.get_schema'])
    @depends(after='test_get_schema')
    def test_get_schema_content(self):
        # """ Testing GET /SchemaStore/en/{identifier} """
        self.assertNotEqual([], self.__class__.__locationUri)
        for member in self.__class__.__locationUri:
            self.assertNotEqual(None, member)
            dataId = member.split('/redfish/v1/SchemaStore/en/')[1]
            redfish().get_schema_content(dataId)
            # todo: I assume someone wants to do something with this value

    # @test(groups=['redfish.get_schema_content_invalid'], depends_on_groups=['redfish.get_schema'])
    @depends(after='test_get_schema')
    def test_get_schema_content_invalid(self):
        # """ Testing GET /Schemas/en/{identifier} 404s properly """
        self.assertNotEqual([], self.__class__.__locationUri)
        for member in self.__class__.__locationUri:
            self.assertNotEqual(None, member)
            dataId = member.split('/redfish/v1/SchemaStore/en/')[1]
            try:
                redfish().get_schema_content(dataId + '-invalid')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))
            break
