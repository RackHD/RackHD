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

@test(groups=['redfish.schema.tests'], depends_on_groups=['obm.tests'])
class SchemaTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__schemaList = None
        self.__membersList = None
        self.__locationUri = []

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['redfish.list_schemas'])
    def test_list_schemas(self):
        """ Testing GET /Schemas """
        redfish().list_schemas()
        schemas = self.__get_data()
        LOG.debug(schemas,json=True)
        assert_not_equal(0, len(schemas), message='Schema list was empty!')
        self.__schemaList = schemas

    @test(groups=['redfish.get_schema'], depends_on_groups=['redfish.list_schemas'])
    def test_get_schema(self):
        """ Testing GET /Schemas/{identifier} """
        self.__membersList = self.__schemaList.get('Members')
        assert_not_equal(None, self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/Schemas/')[1]
            redfish().get_schema(dataId)
            schema_ref = self.__get_data()
            LOG.debug(schema_ref,json=True)
            id = schema_ref.get('Id')
            assert_equal(dataId, id, message='unexpected id {0}, expected {1}'.format(id,dataId))
            assert_equal(type(schema_ref.get('Location')), list, message='expected list not found')
            location = schema_ref.get('Location')[0]
            assert_equal(type(location.get('Uri')), unicode, message='expected uri string not found')
            self.__locationUri.append(location.get('Uri'))

    @test(groups=['redfish.get_schema_invalid'], depends_on_groups=['redfish.list_schemas'])
    def test_get_schema_invalid(self):
        """ Testing GET /Schemas/{identifier} 404s properly """
        self.__membersList = self.__schemaList.get('Members')
        assert_not_equal(None, self.__membersList)
        for member in self.__membersList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/Schemas/')[1]
            try:
                redfish().get_schema(dataId + '-invalid')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))
            break

    @test(groups=['redfish.get_schema_content'], depends_on_groups=['redfish.get_schema'])
    def test_get_schema_content(self):
        """ Testing GET /SchemaStore/en/{identifier} """
        assert_not_equal([], self.__locationUri)
        for member in self.__locationUri:
            assert_not_equal(None,member)
            dataId = member.split('/redfish/v1/SchemaStore/en/')[1]
            redfish().get_schema_content(dataId)
            schema_file_contents = self.__get_data()

    @test(groups=['redfish.get_schema_content_invalid'], depends_on_groups=['redfish.get_schema'])
    def test_get_schema_content_invalid(self):
        """ Testing GET /Schemas/en/{identifier} 404s properly """
        assert_not_equal([], self.__locationUri)
        for member in self.__locationUri:
            assert_not_equal(None,member)
            dataId = member.split('/redfish/v1/SchemaStore/en/')[1]
            try:
                redfish().get_schema_content(dataId + '-invalid')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))
            break

