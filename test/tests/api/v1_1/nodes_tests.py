from config.api1_1_config import *
from config.amqp import *
from modules.logger import Log
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import WorkflowApi as Workflows
from on_http_api1_1 import rest
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import assert_true
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import loads
from time import sleep

LOG = Log(__name__)

@test(groups=['nodes.tests'])
class NodesTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__task = None
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
    
    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __get_workflow_status(self, id):
        Nodes().nodes_identifier_workflows_active_get(id)
        status = self.__client.last_response.status
        if status == 200:
            data = self.__get_data()
            status = data.get('_status')
            assert_is_not_none(status)
        return status

    def __post_workflow(self, id, graph_name, data):
        status = self.__get_workflow_status(id)
        if status != 'pending' and status != 'running':
            Nodes().nodes_identifier_workflows_post(id,graph_name,body=data)
        timeout = 20
        while status != 'pending' and status != 'running' and timeout != 0:
            LOG.warning('Workflow status for Node {0} (status={1},timeout={2})'.format(id,status,timeout))
            status = self.__get_workflow_status(id)
            sleep(1)
            timeout -= 1
        return timeout

    def check_compute_count(self):
        Nodes().nodes_get()
        nodes = self.__get_data()
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
        self.__task = WorkerThread(AMQPWorker(queue=QUEUE_GRAPH_FINISH, \
                                              callbacks=[self.handle_graph_finish]), 'discovery')
        def start(worker,id):
            worker.start()
        tasks = WorkerTasks(tasks=[self.__task], func=start)
        tasks.run()
        tasks.wait_for_completion(timeout_sec=1200)
        assert_false(self.__task.timeout, \
            message='timeout waiting for task {0}'.format(self.__task.id))

    def handle_graph_finish(self,body,message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        Workflows().workflows_get()
        workflows = self.__get_data()
        message.ack()
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
                        break
        check = self.check_compute_count()
        if check and check == self.__discovered:
            self.__task.worker.stop()
            self.__task.running = False
            self.__discovered = 0

    @test(groups=['test-nodes'], depends_on_groups=['nodes.discovery.test'])
    def test_nodes(self):
        """ Testing GET:/nodes """
        Nodes().nodes_get()
        nodes = self.__get_data()
        LOG.debug(nodes,json=True)
        assert_not_equal(0, len(nodes), message='Node list was empty!')

    @test(groups=['test-node-id'], depends_on_groups=['test-nodes'])
    def test_node_id(self):
        """ Testing GET:/nodes/:id """
        Nodes().nodes_get()
        nodes = self.__get_data()
        LOG.debug(nodes,json=True)
        codes = []
        for n in nodes:
            LOG.info(n)
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Nodes().nodes_identifier_get(uuid)
                rsp = self.__client.last_response
                codes.append(rsp)
        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().nodes_identifier_get, 'fooey')

    @test(groups=['create-node'], depends_on_groups=['test-node-id'])
    def test_node_create(self):
        """ Verify POST:/nodes/ """
        for n in self.__test_nodes:
            LOG.info('Creating node (name={0})'.format(n.get('name')))
            Nodes().nodes_post(n)
            rsp = self.__client.last_response
            assert_equal(201, rsp.status, message=rsp.reason)

    @test(groups=['test-node-id-obm'], depends_on_groups=['create-node'])
    def test_node_id_obm(self):
        """ Testing GET:/nodes/:id/obm """
        Nodes().nodes_get()
        nodes = self.__get_data()
        LOG.debug(nodes,json=True)
        codes = []
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                uuid = n.get('id')
                Nodes().nodes_identifier_obm_get(uuid)
                rsp = self.__client.last_response
                LOG.info('OBM setting for node ID {0} is {1}'.format(uuid, rsp.data))
                codes.append(rsp)

        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().nodes_identifier_obm_get, 'fooey')

    @test(groups=['patch-node'], depends_on_groups=['test-node-id-obm'])
    def test_node_patch(self):
        """ Verify PATCH:/nodes/:id """
        data = {"name": 'fake_name_test'}
        Nodes().nodes_get()
        nodes = self.__get_data()
        codes = []
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                uuid = n.get('id')
                Nodes().nodes_identifier_patch(uuid, data)
                rsp = self.__client.last_response
                test_nodes = self.__get_data()
                assert_equal(test_nodes.get('name'), 'fake_name_test', 'Oops patch failed')
                codes.append(rsp)
                LOG.info('Restoring name to "test_compute_node"')
                correct_data = {"name": 'test_compute_node'}
                Nodes().nodes_identifier_patch(uuid, correct_data)
                rsp = self.__client.last_response
                restored_nodes = self.__get_data()
                assert_equal(restored_nodes.get('name'), 'test_compute_node', 'Oops restoring failed')
                codes.append(rsp)
        assert_not_equal(0, len(codes), message='Failed to find compute node Ids')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().nodes_identifier_patch, 'fooey', data)

    @test(groups=['delete-node'], depends_on_groups=['patch-node'])
    def test_node_delete(self):
        """ Testing DELETE:/nodes/:id """
        codes = []
        test_names = []
        Nodes().nodes_get()
        nodes = self.__get_data()
        test_names = [t.get('name') for t in self.__test_nodes]
        for n in nodes:
            name = n.get('name')
            if name in test_names:
                uuid = n.get('id')
                LOG.info('Deleting node {0} (name={1})'.format(uuid, name))
                Nodes().nodes_identifier_delete(uuid)
                codes.append(self.__client.last_response)

        assert_not_equal(0, len(codes), message='Delete node list empty!')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().nodes_identifier_delete, 'fooey')

    @test(groups=['create-whitelist-node'], depends_on_groups=['delete-node'])
    def test_whitelist_node_create(self):
        """ Verify POST:/nodes/:mac/dhcp/whitelist """
        Nodes().nodes_get()
        nodes = self.__get_data()
        macList = []
        for n in nodes:
            type = n.get('type')
            assert_is_not_none(type)
            if type == 'compute':
                idList = n.get('identifiers')
                assert_is_not_none(idList)
                if len(idList) > 0:
                    macList.append(idList[0]) # grab the first mac

        for addr in macList:
            LOG.info('whitelisting MAC address {0}'.format(addr))
            Nodes().nodes_macaddress_dhcp_whitelist_post(addr,body={})
            data = self.__get_data()
            assert_not_equal(0, len(data))
            addrParsed = data[0].replace("-", ":")
            LOG.info(addrParsed)
            LOG.info(addr)

    @test(groups=['delete-whitelist-node'], depends_on_groups=['create-whitelist-node'])
    def test_whitelist_node_delete(self):
        """ Verify Delete:/nodes/:mac/dhcp/whitelist """
        Nodes().nodes_get()
        nodes = self.__get_data()
        macList = []
        for n in nodes:
            type = n.get('type')
            assert_is_not_none(type)
            if type == 'compute':
                idList = n.get('identifiers')
                assert_is_not_none(idList)
                if len(idList) > 0:
                    macList.append(idList[0]) # grab the first mac

        for addr in macList:
            LOG.info('Deleting macaddress {0}' .format(addr))
            Nodes().nodes_macaddress_dhcp_whitelist_delete(addr)
            rsp = self.__client.last_response
            assert_equal(204, rsp.status, message=rsp.reason)

    @test(groups=['catalog_nodes', 'check-nodes-catalogs.test'], \
        depends_on_groups=['nodes.discovery.test'])
    def test_node_catalogs(self):
        """ Testing GET id:/catalogs """
        resps = []
        Nodes().nodes_get()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().nodes_identifier_catalogs_get( n.get('id'))
                resps.append(self.__get_data())
        for resp in resps:
            assert_not_equal(0, len(resp), message='Node catalog is empty!')
        assert_raises(rest.ApiException, Nodes().nodes_identifier_catalogs_get, 'fooey')

    @test(groups=['catalog_source'], depends_on_groups=['catalog_nodes'])
    def test_node_catalogs_bysource(self):
        """ Testing GET id:/catalogs/source """
        resps = []
        Nodes().nodes_get()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().nodes_identifier_catalogs_source_get( n.get('id'),'bmc')
                resps.append(self.__client.last_response)
        for resp in resps:
            assert_equal(200,resp.status, message=resp.reason)
        assert_raises(rest.ApiException, Nodes().nodes_identifier_catalogs_source_get, 'fooey','bmc')

    @test(groups=['node_workflows'], depends_on_groups=['nodes.discovery.test'])
    def test_node_workflows_get(self):
        """Testing node GET:id/workflows"""
        resps = []
        Nodes().nodes_get()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().nodes_identifier_workflows_get(n.get('id'))
                resps.append(self.__get_data())
        for resp in resps:
            assert_not_equal(0, len(resp), message='No Workflows found for Node')
        assert_raises(rest.ApiException, Nodes().nodes_identifier_workflows_get, 'fooey')

    @test(groups=['node_post_workflows'], depends_on_groups=['node_workflows'])
    def test_node_workflows_post(self):
        """Testing node POST:id/workflows"""
        resps = []
        Nodes().nodes_get()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                timeout = self.__post_workflow(id,'Graph.Discovery',{})
                if timeout > 0:
                    data = self.__get_data()
                resps.append({'data': data, 'id':id})
        for resp in resps:
            assert_not_equal(0, len(resp['data']),
                message='No Workflows found for Node {0}'.format(resp['id']))
        assert_raises(rest.ApiException, Nodes().nodes_identifier_workflows_post, 'fooey','Graph.Discovery',body={})

    @test(groups=['node_workflows_active'], depends_on_groups=['node_post_workflows'])
    def test_node_workflows_active(self):
        """Testing node GET:id/workflows/active"""
        # test_node_workflows_post verifies the same functionality
        self.test_node_workflows_post()
        assert_raises(rest.ApiException, Nodes().nodes_identifier_workflows_active_get, 'fooey')

    @test(groups=['node_workflows_del_active'], depends_on_groups=['node_workflows_active'])
    def test_node_workflows_del_active(self):
        """Testing node DELETE:id/workflows/active"""
        Nodes().nodes_get()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                timeout = 5
                done = False
                while timeout > 0 and done == False:
                    if 0 == self.__post_workflow(id,'Graph.Discovery',{}):
                        fail('Timed out waiting for graph to start!')
                    try:
                        Nodes().nodes_identifier_workflows_active_delete(id)
                        done = True
                    except rest.ApiException as e:
                        if e.status != 404:
                            raise e
                        timeout -= 1
        assert_raises(rest.ApiException, Nodes().nodes_identifier_workflows_active_delete, 'fooey')

