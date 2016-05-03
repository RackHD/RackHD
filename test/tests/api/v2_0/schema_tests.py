from config.api2_0_config import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as api20
from on_http_api2_0 import rest
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis.asserts import fail
from proboscis import test
from json import loads,dumps

LOG = Log(__name__)

@test(groups=['schemas_api2.tests'])
class SchemaTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__schemaList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['2.0.list_schemas'])
    def test_list_schemas(self):
        """ Testing GET /api/2.0/schemas """
        api20().schemas_get()
        schemas = self.__get_data()
        LOG.debug(schemas,json=True)
        assert_not_equal(0, len(schemas), message='Schema list was empty')
        self.__schemaList = schemas

    @test(groups=['2.0.get_schema'], depends_on_groups=['2.0.list_schemas'])
    def test_get_schema(self):
        """ Testing GET /api/2.0/schemas/{identifier} """
        assert_not_equal(None, self.__schemaList)
        for member in self.__schemaList:
            assert_not_equal(None,member)
            dataId = member.split('/api/2.0/schemas/')[1]
            api20().schemas_id_get(dataId)
            schema_ref = self.__get_data()
            LOG.debug(schema_ref,json=True)
            id = schema_ref.get('title')
            assert_true('title' in schema_ref.keys(), message='title not found in schema')
            assert_true('definitions' in schema_ref.keys(), message='definitions not found in schema')

    @test(groups=['2.0.get_schema_invalid'], depends_on_groups=['2.0.list_schemas'])
    def test_get_schema_invalid(self):
        """ Testing GET /api/2.0/schemas/{identifier} 404s properly """
        assert_not_equal(None, self.__schemaList)
        for member in self.__schemaList:
            assert_not_equal(None,member)
            try:
                api20().schemas_id_get(member + '-invalid')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))
            break
