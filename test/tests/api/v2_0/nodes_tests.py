from config.api1_1_config import config as config_old   #TODO remove when 2.0 worklfow API is implemented
from config.api2_0_config import config
from config.amqp import *
from modules.logger import Log
from modules.amqp import AMQPWorker
from on_http_api1_1 import WorkflowApi as Workflows  #TODO remove when 2.0 worklfow API is implemented
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import loads
from time import sleep

LOG = Log(__name__)

@test(groups=['nodes_api2.tests'])
class NodesTests(object):

    def __init__(self):
        self.__client_old = config_old.api_client
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
        self.__test_tags = {
            'tags': ['tag1', 'tag2']
        }
        
    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __get_workflow_status(self, id):
        Api().nodes_get_active_workflow_by_id(identifier=id)
        status = self.__client.last_response.status
        if status == 200:
            data = self.__get_data()
            if data:
                status = data.get('_status')
                assert_is_not_none(status)
        return status
        
    def __post_workflow(self, id, graph_name):
        status = self.__get_workflow_status(id)
        if status != 'pending' and status != 'running':
            Api().nodes_post_workflow_by_id(identifier=id, name=graph_name, body={'name': graph_name})
        timeout = 20
        while status != 'pending' and status != 'running' and timeout != 0:
            LOG.warning('Workflow status for Node {0} (status={1},timeout={2})'.format(id,status,timeout))
            status = self.__get_workflow_status(id)
            sleep(1)
            timeout -= 1
        return timeout

    def check_compute_count(self):
        Api().nodes_get_all()
        nodes = self.__get_data()
        count = 0
        for n in nodes:
            type = n.get('type')
            if type == 'compute':
                count += 1
        return count

    @test(groups=['nodes.api2.discovery.test'])
    def test_nodes_discovery(self):
        """ API 2.0 Testing Graph.Discovery completion """
        if self.check_compute_count():
            LOG.warning('Nodes already discovered!')
            return
        self.__discovery_duration = datetime.now()
        LOG.info('Wait start time: {0}'.format(self.__discovery_duration))
        self.__worker = AMQPWorker(queue=QUEUE_GRAPH_FINISH,callbacks=[self.handle_graph_finish])
        self.__worker.start()

    def handle_graph_finish(self,body,message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        Workflows().workflows_get()  #TODO replace with 2.0 workflow API
        workflows = self.__get_data()
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

    @test(groups=['test-nodes-api2'], depends_on_groups=['nodes.api2.discovery.test'])
    def test_nodes(self):
        """ Testing GET:/api/2.0/nodes """
        Api().nodes_get_all()
        nodes = self.__get_data()
        LOG.debug(nodes,json=True)
        assert_not_equal(0, len(nodes), message='Node list was empty!')

    @test(groups=['test-node-id-api2'], depends_on_groups=['test-nodes-api2'])
    def test_node_id(self):
        """ Testing GET:/api/2.0/nodes/:id """
        Api().nodes_get_all()
        nodes = self.__get_data()
        LOG.debug(nodes,json=True)
        codes = []
        for n in nodes:
            LOG.info(n,json=True)
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Api().nodes_get_by_id(identifier=uuid)
                rsp = self.__client.last_response
                codes.append(rsp)
        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_get_by_id, 'fooey')

    @test(groups=['create-node-api2'], depends_on_groups=['test-node-id-api2'])
    def test_node_create(self):
        """ Testing POST:/api/2.0/nodes/ """
        for n in self.__test_nodes:
            LOG.info('Creating node (name={0})'.format(n.get('name')))
            Api().nodes_post(identifiers=n)
            rsp = self.__client.last_response
            assert_equal(201, rsp.status, message=rsp.reason)

    @test(groups=['test-node-id-obm-api2'], depends_on_groups=['create-node-api2'])
    def test_node_id_obm(self):
        """ Testing GET:/api/2.0/nodes/:id/obm """
        Api().nodes_get_all()
        nodes = self.__get_data()
        LOG.debug(nodes,json=True)
        codes = []
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                uuid = n.get('id')
                Api().nodes_get_obm_by_id(identifier=uuid)
                rsp = self.__client.last_response
                LOG.info('OBM setting for node ID {0} is {1}'.format(uuid, rsp.data))
                codes.append(rsp)

        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_get_obm_by_id, 'fooey')

    @test(groups=['patch-node-api2'], depends_on_groups=['test-node-id-api2'])
    def test_node_patch(self):
        """ Testing PATCH:/api/2.0/nodes/:id """
        data = {"name": 'fake_name_test'}
        Api().nodes_get_all()
        nodes = self.__get_data()
        codes = []
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                uuid = n.get('id')
                Api().nodes_patch_by_id(identifier=uuid,body=data)
                rsp = self.__client.last_response
                test_nodes = self.__get_data()
                assert_equal(test_nodes.get('name'), 'fake_name_test', 'Oops patch failed')
                codes.append(rsp)
                LOG.info('Restoring name to "test_compute_node"')
                correct_data = {"name": 'test_compute_node'}
                Api().nodes_patch_by_id(identifier=uuid,body=correct_data)
                rsp = self.__client.last_response
                restored_nodes = self.__get_data()
                assert_equal(restored_nodes.get('name'), 'test_compute_node', 'Oops restoring failed')
                codes.append(rsp)
        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_patch_by_id, 'fooey', data)

    @test(groups=['delete-node-api2'], depends_on_groups=['patch-node-api2'])
    def test_node_delete(self):
        """ Testing DELETE:/api/2.0/nodes/:id """
        codes = []
        test_names = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        test_names = [t.get('name') for t in self.__test_nodes]
        for n in nodes:
            name = n.get('name')
            if name in test_names:
                uuid = n.get('id')
                LOG.info('Deleting node {0} (name={1})'.format(uuid, name))
                Api().nodes_del_by_id(identifier=uuid)
                codes.append(self.__client.last_response)

        assert_not_equal(0, len(codes), message='Delete node list empty!')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_del_by_id, 'fooey')

    @test(groups=['catalog_nodes-api2'], depends_on_groups=['delete-whitelist-node-api2'])
    def test_node_catalogs(self):
        """ Testing GET:/api/2.0/nodes/:id/catalogs """
        resps = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().nodes_get_catalog_by_id(identifier=n.get('id'))
                resps.append(self.__get_data())
        for resp in resps:
            assert_not_equal(0, len(resp), message='Node catalog is empty!')
        assert_raises(rest.ApiException, Api().nodes_get_catalog_by_id, 'fooey')

    @test(groups=['catalog_source-api2'], depends_on_groups=['catalog_nodes-api2'])
    def test_node_catalogs_bysource(self):
        """ Testing GET:/api/2.0/nodes/:id/catalogs/source """
        resps = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().nodes_get_catalog_source_by_id(identifier=n.get('id'), source='bmc')
                resps.append(self.__client.last_response)
        for resp in resps:
            assert_equal(200,resp.status, message=resp.reason)
        assert_raises(rest.ApiException, Api().nodes_get_catalog_source_by_id, 'fooey','bmc')

    @test(groups=['node_workflows-api2'], depends_on_groups=['catalog_source-api2'])
    def test_node_workflows_get(self):
        """ Testing GET:/api/2.0/nodes/:id/workflows """
        resps = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().nodes_get_workflow_by_id(identifier=n.get('id'))
                resps.append(self.__get_data())
        for resp in resps:
            assert_not_equal(0, len(resp), message='No Workflows found for Node')
        assert_raises(rest.ApiException, Api().nodes_get_workflow_by_id, 'fooey')

    @test(groups=['node_post_workflows-api2'], depends_on_groups=['node_workflows-api2'])
    def test_node_workflows_post(self):
        """ Testing POST:/api/2.0/nodes/:id/workflows """
        resps = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                timeout = self.__post_workflow(id,'Graph.Discovery')
                if timeout > 0:
                    data = self.__get_data()
                resps.append({'data': data, 'id':id})
        for resp in resps:
            assert_not_equal(0, len(resp['data']), 
                message='No Workflows found for Node {0}'.format(resp['id']))
        assert_raises(rest.ApiException, Api().nodes_post_workflow_by_id, 'fooey',name='Graph.Discovery',body={})

    @test(groups=['node_workflows_active-api2'], depends_on_groups=['node_post_workflows-api2'])
    def test_node_workflows_active(self):
        """ Testing GET:/api/2.0/nodes/:id/workflows/active """
        # test_node_workflows_post verifies the same functionality
        self.test_node_workflows_post()
        assert_raises(rest.ApiException, Api().nodes_get_active_workflow_by_id, 'fooey')

    @test(groups=['node_workflows_del_active-api2'], depends_on_groups=['node_workflows_active-api2'])
    def test_node_workflows_del_active(self):
        """ Testing DELETE:/api/2.0/nodes/:id/workflows/active """
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                timeout = 5
                done = False
                while timeout > 0 and done == False:
                    if 0 == self.__post_workflow(id,'Graph.Discovery'):
                        fail('Timed out waiting for graph to start!')
                    try:
                        Api().nodes_del_active_workflow_by_id(identifier=id)
                        done = True
                    except rest.ApiException as e:
                        if e.status != 404:
                            raise e
                        timeout -= 1
                assert_not_equal(timeout, 0, message='Failed to delete an active workflow')
        assert_raises(rest.ApiException, Api().nodes_del_active_workflow_by_id, 'fooey')

    @test(groups=['node_tags_patch'], depends_on_groups=['node_workflows_del_active-api2'])
    def test_node_tags_patch(self):
        """ Testing PATCH:/api/2.0/nodes/:id/tags """
        codes = []
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        codes.append(rsp)
        for n in nodes:
            LOG.info(n, json=True)
            Api().nodes_patch_tag_by_id(identifier=n.get('id'), body=self.__test_tags)
            LOG.info('Creating tag (name={0})'.format(self.__test_tags))
            rsp = self.__client.last_response
            codes.append(rsp)
            LOG.info(n.get('id'));
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_patch_tag_by_id, 'fooey',body=self.__test_tags)

    @test(groups=['node_tags_get'], depends_on_groups=['node_tags_patch'])
    def test_node_tags_get(self):
        """ Testing GET:api/2.0/nodes/:id/tags """
        codes = []
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        codes.append(rsp)
        for n in nodes:
            Api().nodes_get_tags_by_id(n.get('id'))
            rsp = self.__client.last_response
            tags = loads(rsp.data)
            codes.append(rsp)
            for t in self.__test_tags.get('tags'):
                assert_true(t in tags, message= "cannot find new tag" )
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_patch_tag_by_id, 'fooey',body=self.__test_tags)


    @test(groups=['node_tags_delete'], depends_on_groups=['node_tags_get'])
    def test_node_tags_del(self):
        """ Testing DELETE:api/2.0/nodes/:id/tags/:tagName """
        codes = []
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        codes.append(rsp)
        for n in nodes:
            for t in self.__test_tags.get('tags'):
                Api().nodes_del_tag_by_id(identifier=n.get('id'), tag_name=t)
                rsp = self.__client.last_response
                codes.append(rsp)
            Api().nodes_get_by_id(identifier=n.get('id'))
            rsp = self.__client.last_response
            codes.append(rsp)
            updated_node = loads(rsp.data)
            for t in self.__test_tags.get('tags'):
                assert_true(t not in updated_node.get('tags'), message= "Tag " + t + " was not deleted" )
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_del_tag_by_id, 'fooey',tag_name=['tag'])


    @test(groups=['nodes_tag_masterDelete'], depends_on_groups=['node_tags_delete'])
    def test_node_tags_masterDel(self):
        """ Testing DELETE:api/2.0/nodes/tags/:tagName """
        codes = []
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        codes.append(rsp)
        self.test_node_tags_patch()
        t = 'tag3'
        for n in nodes:
            Api().nodes_master_del_tag_by_id(tag_name=t)
            rsp = self.__client.last_response
            codes.append(rsp)
            Api().nodes_get_by_id(identifier=n.get('id'))
            rsp = self.__client.last_response
            codes.append(rsp)
            updated_node = loads(rsp.data)
            assert_true(t not in updated_node.get('tags'), message= "Tag " + t + " was not deleted" )
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
            LOG.info(c.status)

