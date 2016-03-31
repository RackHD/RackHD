from config.api2_0_config import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads
from on_http_api2_0 import rest


LOG = Log(__name__)


@test(groups=['catalogs_api2.tests'])
class CatalogsTests(object):
    def __init__(self):
        self.__client = config.api_client

    @test(groups=['catalogs_api2.tests', 'api2_check-catalogs'])
    def test_catalogs(self):
        """Testing GET:api/2.0/catalogs to get list of catalogs"""
        Api().get_catalog()
        rsp = self.__client.last_response
        assert_not_equal(404, rsp.status, message=rsp.reason)
        assert_equal(200, rsp.status, message=rsp.reason)


    @test(groups=['catalogs_api2.tests'], depends_on_groups=['api2_check-catalogs'])
    def test_catalogs_id(self):
        """Testing GET:api/2.0/catalogs/id to get specific catalog details"""
        Api().get_catalog()
        catalogs = loads(self.__client.last_response.data)
        codes = []
        for n in catalogs:
            id = n.get('id')
            assert_is_not_none(id)
            Api().get_catalog_by_id(identifier=id)
            rsp = self.__client.last_response
            assert_not_equal(404, rsp.status, message=rsp.reason)
            codes.append(rsp)
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().get_catalog_by_id, 'fooey')
