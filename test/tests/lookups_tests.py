from modules.lookups import Lookups
from modules.nodes import Nodes
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
from json import dumps

LOG = Log(__name__)

@test(groups=['lookups.tests'])
class LookupsTests(object):

    def __init__(self):
        pass

    @test(groups=['lookups.tests', 'check-lookups'], depends_on_groups=['nodes.tests'])
    def check_lookups(self):
        """ Testing GET:/lookups """
        nodes = Nodes().get_nodes().json()
        assert_not_equal(0,nodes, message='Node list was empty!')
        rsp = Lookups().get_lookups()
        assert_equal(200,rsp.status_code, message='Unexpected lookups response code {0}'.format(rsp.status_code))
        lookups = rsp.json()
        obms = [ n.get('obmSettings') for n in nodes if n.get('obmSettings') is not None ]
        hosts = []
        for o in obms:
            for c in o:
                hosts.append(c.get('config').get('host'))
        assert_not_equal(0, len(hosts))
        LOG.debug(hosts,json=True)
        LOG.debug(lookups,json=True)
        for h in hosts:
            assert_true(h in dumps(lookups))

    @test(depends_on_groups=['check-lookups'])
    def check_lookup_query(self):
        """ Testing GET:/lookups?q=t """
        nodes = Nodes().get_nodes().json()
        assert_not_equal(0,nodes, message='Node list was empty!')
        rsp = Lookups().get_lookups()
        lookups = rsp.json()
        LOG.debug(lookups,json=True)
        for l in lookups:
            mac = l.get('macAddress')
            assert_true(mac is not None)
            rsp = Lookups().get_lookups(query=mac)
            assert_equal(200,rsp.status_code)




