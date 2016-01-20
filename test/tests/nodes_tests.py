from config.settings import *
from config.amqp import *
from modules.logger import Log
from modules.amqp import Worker
from on_http import NodesApi as Nodes
from on_http import WorkflowsApi as Workflows
from on_http import rest
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import loads

LOG = Log(__name__)

@test(groups=['nodes.tests'])
class NodesTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__worker = None
        self.__discovery_duration = None
        self.__discovered = 0
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
                    'config': {'host': '00:01:02:03:04:05', 'password': 'pass', 'user': 'user'},
                    'service': 'ipmi-obm-service'
                }]
            }
        ]

    def check_compute_count(self):
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        count = 0
        for n in nodes:
            type = n.get('type')
            if type == 'compute':
                count += 1
        return count

    @test(groups=['nodes.discovery.test'])
    def test_nodes_discovery(self):
        """ Testing Graph.Discovery completion """
        if self.check_compute_count():
            LOG.warning('Nodes already discovered!')
            return
        self.__discovery_duration = datetime.now()
        LOG.info('Wait start time: {0}'.format(self.__discovery_duration))
        self.__worker = Worker(queue=QUEUE_GRAPH_FINISH,callbacks=[self.handle_graph_finish])
        self.__worker.start()

    def handle_graph_finish(self,body,message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        Workflows().api1_1_workflows_get()
        workflows = loads(self.__client.last_response.data)
        for w in workflows:
            definition = w['definition']
            injectableName = definition.get('injectableName') 
            if injectableName == 'Graph.SKU.Discovery':
                graphId = w['context'].get('graphId')
                if graphId == routeId:
                    status = body.get('status')
                    if status == 'succeeded':
                        options = definition.get('options')
                        nodeid = options['defaults'].get('nodeId')
                        duration = datetime.now() - self.__discovery_duration
                        LOG.info('{0} - target: {1}, status: {2}, route: {3}, duration: {4}'
                                .format(injectableName,nodeid,status,routeId,duration))
                        self.__discovered += 1
                        message.ack()
                        break
        check = self.check_compute_count()
        if check and check == self.__discovered:
            self.__worker.stop()
            self.__worker = None
            self.__discovered = 0

    @test(groups=['test-nodes'], depends_on_groups=['nodes.discovery.test'])
    def test_nodes(self):
        """ Testing GET:/nodes """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        LOG.debug(nodes,json=True)
        assert_not_equal(0, len(nodes), message='Node list was empty!')

    @test(groups=['test-node-id'], depends_on_groups=['test-nodes'])
    def test_node_id(self):
        """ Testing GET:/nodes/:id """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        LOG.debug(nodes,json=True)
        codes = []
        for n in nodes:
            LOG.info(n)
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Nodes().api1_1_nodes_identifier_get(uuid)
                rsp = self.__client.last_response
                codes.append(rsp)
        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_get, 'fooey')

    @test(groups=['create-node'], depends_on_groups=['test-node-id'])
    def test_node_create(self):
        """ Verify POST:/nodes/ """
        for n in self.__test_nodes:
            LOG.info('Creating node (name={0})'.format(n.get('name')))
            Nodes().api1_1_nodes_post(n)
            rsp = self.__client.last_response
            assert_equal(201, rsp.status, message=rsp.reason)

    @test(groups=['test-node-id-obm'], depends_on_groups=['create-node'])
    def test_node_id_obm(self):
        """ Testing GET:/nodes/:id/obm """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        LOG.debug(nodes,json=True)
        codes = []
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                uuid = n.get('id')
                Nodes().api1_1_nodes_identifier_obm_get(uuid)
                rsp = self.__client.last_response
                LOG.info('OBM setting for node ID {0} is {1}'.format(uuid, rsp.data))
                codes.append(rsp)

        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_obm_get, 'fooey')

    @test(groups=['patch-node'], depends_on_groups=['test-node-id-obm'])
    def test_node_patch(self):
        """ Verify PATCH:/nodes/:id """
        data = {"name": 'fake_name_test'}
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        codes = []
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                uuid = n.get('id')
                Nodes().api1_1_nodes_identifier_patch(uuid, data)
                rsp = self.__client.last_response
                test_nodes = loads(self.__client.last_response.data)
                assert_equal(test_nodes.get('name'), 'fake_name_test', 'Oops patch failed')
                codes.append(rsp)
                LOG.info('Restoring name to "test_compute_node"')
                correct_data = {"name": 'test_compute_node'}
                Nodes().api1_1_nodes_identifier_patch(uuid, correct_data)
                rsp = self.__client.last_response
                restored_nodes = loads(self.__client.last_response.data)
                assert_equal(restored_nodes.get('name'), 'test_compute_node', 'Oops restoring failed')
                codes.append(rsp)
        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_patch, 'fooey', data)

    @test(groups=['delete-node'], depends_on_groups=['patch-node'])
    def test_node_delete(self):
        """ Testing DELETE:/nodes/:id """
        codes = []
        test_names = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        test_names = [t.get('name') for t in self.__test_nodes]
        for n in nodes:
            name = n.get('name')
            if name in test_names:
                uuid = n.get('id')
                LOG.info('Deleting node {0} (name={1})'.format(uuid, name))
                Nodes().api1_1_nodes_identifier_delete(uuid)
                codes.append(self.__client.last_response)

        assert_not_equal(0, len(codes), message='Delete node list empty!')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_delete, 'fooey')

    @test(groups=['create-whitelist-node'], depends_on_groups=['delete-node'])
    def test_whitelist_node_create(self):
        """ Verify POST:/nodes/:mac/dhcp/whitelist """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            for i in n:
                if i == 'identifiers':
                    if len(n[i]) > 0:
                        macaddress = n[i]
                        LOG.info('Posting macaddress {0}' .format(macaddress))


        for address in macaddress:
            Nodes().api1_1_nodes_macaddress_dhcp_whitelist_post(address, n)
            rsp = self.__client.last_response
            assert_equal(201, rsp.status, message=rsp.reason)
            macaddress_parsed = loads(rsp.data.replace("-", ":"))
            if macaddress_parsed[len(macaddress_parsed)-1] == macaddress[len(macaddress)-1]:
                LOG.info("Verfied the macaddress on whitelist")

    @test(groups=['delete-whitelist-node'], depends_on_groups=['create-whitelist-node'])
    def test_whitelist_node_delete(self):
        """ Verify Delete:/nodes/:mac/dhcp/whitelist """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            for i in n:
                if i == 'identifiers':
                    if len(n[i]) > 0:
                        macaddress = n[i]

        macaddress_to_delete = macaddress[len(macaddress)-1]
        LOG.info('Deleting macaddress {0}' .format(macaddress_to_delete))
        Nodes().api1_1_nodes_macaddress_dhcp_whitelist_delete(macaddress_to_delete)
        rsp = self.__client.last_response
        assert_equal(204, rsp.status, message=rsp.reason)

    @test(groups=['catalog_nodes'], depends_on_groups=['delete-whitelist-node'])
    def test_node_catalogs(self):
        """ Testing GET id:/catalogs """
        resps = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().api1_1_nodes_identifier_catalogs_get( n.get('id'))
                resps.append(self.__client.last_response.data)
        for resp in resps:
            assert_not_equal(0, len(loads(resp)), message='Node catalog is empty!')
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_catalogs_get, 'fooey')

    @test(groups=['catalog_source'], depends_on_groups=['catalog_nodes'])
    def test_node_catalogs_bysource(self):
        """ Testing GET id:/catalogs/source """
        resps = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().api1_1_nodes_identifier_catalogs_source_get( n.get('id'),'bmc')
                resps.append(self.__client.last_response)
        for resp in resps:
            assert_equal(200,resp.status, message=resp.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_catalogs_source_get, 'fooey','bmc')

    @test(groups=['node_workflows'], depends_on_groups=['catalog_source'])
    def test_node_workflows_get(self):
        """Testing node GET:id/workflows"""
        resps = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().api1_1_nodes_identifier_workflows_get(n.get('id'))
                resps.append(self.__client.last_response.data)
        for resp in resps:
            assert_not_equal(0, len(loads(resp)), message='No Workflows found for Node')
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_workflows_get, 'fooey')

    @test(groups=['node_post_workflows'], depends_on_groups=['node_workflows'])
    def test_node_workflows_post(self):
        """Testing node POST:id/workflows"""
        resps = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().api1_1_nodes_identifier_workflows_post(n.get('id'),name='Graph.Discovery',body={})
                resps.append(self.__client.last_response.data)
        for resp in resps:
            assert_not_equal(0, len(loads(resp)), message='No Workflows found for Node')
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_workflows_post, 'fooey','Graph.Discovery',{})

    @test(groups=['node_workflows_active'], depends_on_groups=['node_post_workflows'])
    def test_node_workflows_active(self):
        """Testing node GET:id/workflows/active"""
        resps = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().api1_1_nodes_identifier_workflows_active_get(n.get('id'))
                resps.append(self.__client.last_response.data)
        for resp in resps:
            assert_not_equal(0, len(loads(resp)), message='No active Workflows found for Node')
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_workflows_active_get, 'fooey')

    @test(groups=['node_workflows_del_active'], depends_on_groups=['node_workflows_active'])
    def test_node_workflows_del_active(self):
        """Testing node DELETE:id/workflows/active"""
        resps = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().api1_1_nodes_identifier_workflows_active_delete(n.get('id'))
                resps.append(self.__client.last_response.data)
        for resp in resps:
            assert_not_equal(0, len(loads(resp)), message='No active Workflows found for Node')
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_workflows_active_delete, 'fooey')

