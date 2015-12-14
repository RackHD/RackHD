from config.settings import *
from modules.nodes import Nodes
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)

@test(groups=['nodes.tests'])
class NodesTests(object):

    def __init__(self):
        self.__test_nodes = [
            {
                'autoDiscover': 'false',
                'name': 'test_switch_node',
                'type': 'switch',
                'obmSettings': [{
                    'config': { 'host': '1.1.1.1', 'community': 'rackhd' },
                    'service': 'snmp-obm-service'
                }]
            },
            {
                'autoDiscover': 'false',
                'name': 'test_mgmt_node',
                'type': 'mgmt',
                'obmSettings': [{
                    'config': { 'host': '1.1.1.1', 'community': 'rackhd' },
                    'service': 'snmp-obm-service'
                }]
            },
            {
                'autoDiscover': 'false',
                'name': 'test_pdu_node',
                'type': 'pdu',
                'obmSettings': [{
                    'config': { 'host': '1.1.1.2', 'community': 'rackhd' },
                    'service': 'snmp-obm-service'
                }]
            },
            {
                'autoDiscover': 'false',
                'name': 'test_enclosure_node',
                'type': 'enclosure'
            },
            {
                'autoDiscover': 'false',
                'name': 'test_compute_node',
                'type': 'compute',
                'obmSettings': [{
                    'config': { 'host': '00:01:02:03:04:05', 'password': 'pass', 'user': 'user' },
                    'service': 'ipmi-obm-service'
                }]
            }
        ]

    @test(groups=['nodes.test','test-nodes'])
    def test_nodes(self):
        """ Testing GET:/nodes API """
        rsp = Nodes().get_nodes()
        nodes = rsp.json()
        LOG.debug(nodes,json=True)
        assert_equal(200,rsp.status_code)
        assert_not_equal(len(nodes), 0, message='Node list was empty!')

    @test(groups=['test-node-id'], depends_on_groups=['test-nodes'])
    def test_node_id(self):
        """ Testing GET:/nodes/:id API """
        rsp = Nodes().get_nodes()
        nodes = rsp.json()
        for n in nodes:
            if n.get('type') == 'compute':
                uuid = n.get('id')
                rsp = Nodes().get_nodes(uid=uuid)
                assert_equal(200,rsp.status_code, message='Unexpected response {0} for node {1}'.format(rsp.status_code,uuid))
        rsp = Nodes().get_nodes(uid='fooey')
        assert_equal(404, rsp.status_code, message='Expected failure for invalid node')

    @test(groups=['create-node'], depends_on_groups=['test-nodes'])
    def test_node_create(self):
        """ Verfiy POST:/nodes/ """
        for n in self.__test_nodes:
            LOG.info(n, json=True)
            rsp = Nodes().post_node(dumps(n))
            assert_equal(201,rsp.status_code, message='Unexpected response {0}'.format(rsp.status_code))
    
    @test(groups=['delete-node'], depends_on_groups=['create-node'])
    def test_node_delete(self):
        """ Testing DELETE:/nodes/:id """
        codes = []
        test_names = []
        rsp = Nodes().get_nodes()
        nodes = rsp.json()
        test_names = [ t.get('name') for t in self.__test_nodes ]
        for n in nodes:
            name = n.get('name')
            if name in test_names:
                uuid = n.get('id')
                LOG.info('Deleting node {0} (name={1})'.format(uuid, name))
                rsp = Nodes().delete_node(uid=uuid)
                codes.append(rsp)
       
        assert_not_equal(0, len(codes), message='Delete node list empty!')
        for c in codes:
            assert_equal(200,c.status_code, message='Unexpected delete response {0}'.format(c.status_code))
        rsp = Nodes().delete_node(uid='fooey')
        assert_equal(404, rsp.status_code, message='Expected delete failure for invalid node')
    




