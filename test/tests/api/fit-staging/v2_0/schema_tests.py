'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as api20
from on_http_api2_0 import rest
from json import loads, dumps
from nose.plugins.attrib import attr
from nosedep import depends

logs = flogging.get_loggers()


# @test(groups=['schemas_api2.tests'])
@attr(regression=False, smoke=True, schema_api2_tests=True)
class SchemaTests(fit_common.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__schemaList = None

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['2.0.list_schemas'])
    def test_list_schemas(self):
        # """ Testing GET /api/2.0/schemas """
        api20().schemas_get()
        schemas = self.__get_data()
        logs.debug(dumps(schemas, indent=4))
        self.assertNotEqual(0, len(schemas), msg='Schema list was empty')
        self.__class__.__schemaList = schemas

    # @test(groups=['2.0.get_schema'], depends_on_groups=['2.0.list_schemas'])
    @depends(after='test_list_schemas')
    def test_get_schema(self):
        # """ Testing GET /api/2.0/schemas/{identifier} """
        self.assertIsNotNone(self.__class__.__schemaList)
        for member in self.__class__.__schemaList:
            self.assertIsNotNone(member)
            dataId = member.split('/api/2.0/schemas/')[1]
            api20().schemas_id_get(dataId)
            schema_ref = self.__get_data()
            logs.debug(dumps(schema_ref, indent=4))
            self.assertIn('title', schema_ref.keys(), msg='title not found in schema')
            self.assertIn('definitions', schema_ref.keys(), msg='definitions not found in schema')

    # @test(groups=['2.0.get_schema_invalid'], depends_on_groups=['2.0.list_schemas'])
    @depends(after='test_list_schemas')
    def test_get_schema_invalid(self):
        # """ Testing GET /api/2.0/schemas/{identifier} 404s properly """
        self.assertIsNotNone(self.__class__.__schemaList)
        for member in self.__class__.__schemaList:
            self.assertIsNotNone(member)
            try:
                api20().schemas_id_get(member + '-invalid')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))
            break
