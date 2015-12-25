from config.settings import *
from modules.logger import Log
from on_http import NodesApi as Nodes
from on_http import rest
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
        self.__client = config.api_client
        self.__test_nodes = [
            {
                'autoDiscover': 'false',
                'name': 'test_switch_node',
                'type': 'switch',
                'snmpSettings': {
                    'host': '1.1.1.1', 
                    'community': 'rackhd'
                }
            },
            {
                'autoDiscover': 'false',
                'name': 'test_mgmt_node',
                'type': 'mgmt',
                'snmpSettings': {
                    'host': '1.1.1.1', 
                    'community': 'rackhd' 
                }
            },
            {
                'autoDiscover': 'false',
                'name': 'test_pdu_node',
                'type': 'pdu',
                'snmpSettings': {
                    'host': '1.1.1.2', 
                    'community': 'rackhd' 
                }
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
        """ Testing GET:/nodes """
        Nodes().api1_1_nodes_get()
        nodes = dumps(self.__client.last_response.data)
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(nodes), message='Node list was empty!')

    @test(groups=['test-node-id'], depends_on_groups=['test-nodes'])
    def test_node_id(self):
        """ Testing GET:/nodes/:id """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        codes = []
        for n in nodes:
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Nodes().api1_1_nodes_identifier_get(uuid)
                rsp = self.__client.last_response
                codes.append(rsp)
        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_get, 'fooey')

    @test(groups=['create-node'], depends_on_groups=['test-nodes'])
    def test_node_create(self):
        """ Verfiy POST:/nodes/ """
        for n in self.__test_nodes:
            LOG.info('Creating node (name={0})'.format(n.get('name')))
            Nodes().api1_1_nodes_post(n)
            rsp = self.__client.last_response
            assert_equal(201, rsp.status, message=rsp.reason)
    
    @test(groups=['delete-node'], depends_on_groups=['create-node'])
    def test_node_delete(self):
        """ Testing DELETE:/nodes/:id """
        codes = []
        test_names = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        test_names = [ t.get('name') for t in self.__test_nodes ]
        for n in nodes:
            name = n.get('name')
            if name in test_names:
                uuid = n.get('id')
                LOG.info('Deleting node {0} (name={1})'.format(uuid, name))
                Nodes().api1_1_nodes_identifier_delete(uuid)
                codes.append(self.__client.last_response)
       
        assert_not_equal(0, len(codes), message='Delete node list empty!')
        for c in codes:
            assert_equal(200,c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_delete, 'fooey')
    




