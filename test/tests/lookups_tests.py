from config.settings import *
from on_http import LookupsApi as Lookups
from on_http import NodesApi as Nodes
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_is_not_none
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)

@test(groups=['lookups.tests'])
class LookupsTests(object):

    def __init__(self):
        self.__client = config.api_client

    @test(groups=['lookups.tests', 'check-lookups-query'], depends_on_groups=['nodes.tests'])
    def check_lookups_query(self):
        """ Testing GET:/lookups?q=term """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        assert_not_equal(0, len(nodes), message='Node list was empty!')
        obms = [ n.get('obmSettings') for n in nodes if n.get('obmSettings') is not None ]
        hosts = []
        for o in obms:
            for c in o:
                hosts.append(c.get('config').get('host'))
        assert_not_equal(0, len(hosts), message='No OBM hosts were found!')
        for host in hosts:
            Lookups().api1_1_lookups_get(q=host)
            rsp = self.__client.last_response
            assert_equal(200, rsp.status, message=rsp.reason)
            assert_not_equal(0, len(rsp.data))

    @test(depends_on_groups=['check-lookups-query'])
    def check_lookup_id(self):
        """ Testing GET:/lookups/:id """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        assert_not_equal(0, len(nodes), message='Node list was empty!')
        obms = [ n.get('obmSettings') for n in nodes if n.get('obmSettings') is not None ]
        assert_not_equal(0, len(obms), message='No OBM settings found!')
        entries = []
        for obm in obms:
            for cfg in obm:
                host = cfg.get('config').get('host')
                Lookups().api1_1_lookups_get(q=host)
                list = loads(self.__client.last_response.data)
                entries.append(list)

        assert_not_equal(0, len(entries), message='No lookup entries found!')
        for entry in entries:
            for id in entry:
                Lookups().api1_1_lookups_id_get(id.get('id'))
                rsp = self.__client.last_response
                assert_equal(200, rsp.status, message=rsp.reason)


