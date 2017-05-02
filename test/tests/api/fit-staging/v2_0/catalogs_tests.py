from config.api2_0_config import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads
from on_http_api2_0 import rest


LOG = Log(__name__)


@test(groups=['catalogs_api2.tests'])
class CatalogsTests(object):
    def __init__(self):
        self.__client = config.api_client
        self.__expected_sources = ['dmi', 'ohai', 'bmc', 'lspci', 'lshw', 'smart']

    @test(groups=['catalogs_api2.tests', 'api2_check-catalogs'])
    def test_catalogs(self):
        """Testing GET:api/2.0/catalogs to get list of catalogs"""

        #get a list of all nodes
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        assert_not_equal(0, len(nodes), message='Node list was empty!')

        #get all catalog data
        Api().catalogs_get()
        rsp = self.__client.last_response
        assert_not_equal(404, rsp.status, message=rsp.reason)
        assert_equal(200, rsp.status, message=rsp.reason)
        catalogs = loads(rsp.data)

        #verify that each node contains a minimum set of catalogs
        for node in nodes:
            if node.get('type') == 'compute':
                for source in self.__expected_sources:
                    for catalog in catalogs:
                        if catalog.get('source') == source and catalog.get('node').find(node.get('id')):
                            break
                    else:
                        fail('Catalog {0} not found in node {1}!'.format(source,node.get('id')))

    @test(groups=['catalogs_api2.tests'], depends_on_groups=['api2_check-catalogs'])
    def test_catalogs_id(self):
        """Testing GET:api/2.0/catalogs/id to get specific catalog details"""
        Api().catalogs_get()
        catalogs = loads(self.__client.last_response.data)
        codes = []
        for n in catalogs:
            id = n.get('id')
            assert_is_not_none(id)
            Api().catalogs_id_get(identifier=id)
            rsp = self.__client.last_response
            assert_not_equal(404, rsp.status, message=rsp.reason)
            catalog = loads(self.__client.last_response.data)
            assert_equal(n, catalog)
            codes.append(rsp)
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().catalogs_id_get, 'fooey')
