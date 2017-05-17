'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from json import loads
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['catalogs_api2.tests'])
@attr(regression=False, smoke=True, catalogs_api2_tests=True)
class CatalogsTests(fit_common.unittest.TestCase):

    def setUp(self):
        self.__client = config.api_client
        self.__expected_sources = ['dmi', 'ohai', 'bmc', 'lspci', 'lshw', 'smart']

    #  @test(groups=['catalogs_api2.tests', 'api2_check-catalogs'])
    def test_catalogs(self):
        # """Testing GET:api/2.0/catalogs to get list of catalogs"""

        # get a list of all nodes
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        self.assertNotEqual(0, len(nodes), msg='Node list was empty!')

        # get all catalog data
        Api().catalogs_get()
        rsp = self.__client.last_response
        self.assertNotEqual(404, rsp.status, msg=rsp.reason)
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        catalogs = loads(rsp.data)

        # verify that each node contains a minimum set of catalogs
        for node in nodes:
            if node.get('type') == 'compute':
                for source in self.__expected_sources:
                    for catalog in catalogs:
                        if catalog.get('source') == source and catalog.get('node').find(node.get('id')):
                            break
                    else:
                        self.fail('Catalog {0} not found in node {1}!'.format(source, node.get('id')))

    # @test(groups=['catalogs_api2.tests'], depends_on_groups=['api2_check-catalogs'])
    @depends(after=test_catalogs)
    def test_catalogs_id(self):
        # """Testing GET:api/2.0/catalogs/id to get specific catalog details"""
        Api().catalogs_get()
        catalogs = loads(self.__client.last_response.data)
        codes = []
        for n in catalogs:
            id = n.get('id')
            self.assertIsNotNone(id)
            Api().catalogs_id_get(identifier=id)
            rsp = self.__client.last_response
            self.assertNotEqual(404, rsp.status, msg=rsp.reason)
            catalog = loads(self.__client.last_response.data)
            self.assertEqual(n, catalog)
            codes.append(rsp)
        for c in codes:
            self.assertEqual(200, c.status, msg=c.reason)
        self.assertRaises(rest.ApiException, Api().catalogs_id_get, 'fooey')
