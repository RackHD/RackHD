'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Author(s):
'''
import fit_path  # NOQA: unused import
import json
import fit_common
import flogging

from config.amqp import QUEUE_GRAPH_FINISH, defaults
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from config.api2_0_config import config
from datetime import datetime
from json import loads
from time import sleep
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['nodes_api2.tests'])
@attr(regression=False, smoke=True, nodes_api2_tests=True)
class NodesTests(fit_common.unittest.TestCase):

    def setUp(self):
        self.__client = config.api_client
        self.__worker = None
        self.__discovery_duration = None
        self.__discovered = 0
        self.__test_nodes = [
            {
                'identifiers': ["FF:FF:FF:01"],
                'autoDiscover': False,
                'name': 'test_switch_node',
                'type': 'switch'
            },
            {
                'identifiers': ["FF:FF:FF:02"],
                'autoDiscover': False,
                'name': 'test_mgmt_node',
                'type': 'mgmt'
            },
            {
                'identifiers': ["FF:FF:FF:03"],
                'autoDiscover': False,
                'name': 'test_pdu_node',
                'type': 'pdu'
            },
            {
                'identifiers': ["FF:FF:FF:04"],
                'autoDiscover': False,
                'name': 'test_enclosure_node',
                'type': 'enclosure'
            },
            {
                'identifiers': ["FF:FF:FF:05"],
                'autoDiscover': False,
                'name': 'test_compute_node',
                'type': 'compute'
            }
        ]
        self.__test_tags = {
            'tags': ['tag1', 'tag2']
        }
        self.__test_obm = {
            'config': {
                'host': '1.2.3.4',
                'user': 'username',
                'password': 'password'
            },
            'service': 'noop-obm-service'
        }

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __get_workflow_status(self, id, query):
        Api().nodes_get_workflow_by_id(identifier=id, active=query)
        data = self.__get_data()
        if len(data) > 0:
            status = data[0].get('_status')
            return status
        return 'not running'

    def __post_workflow(self, id, graph_name):
        status = self.__get_workflow_status(id, 'true')
        if status != 'pending' and status != 'running':
            Api().nodes_post_workflow_by_id(identifier=id, name=graph_name, body={'name': graph_name})
        timeout = 20
        while status != 'pending' and status != 'running' and timeout != 0:
            logs.warning('Workflow status for Node %s (status=%s,timeout=%s)', id, str(status), str(timeout))
            status = self.__get_workflow_status(id, 'true')
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

    def create_temp_nodes(self):
        # utility to create a set of test nodes
        for n in self.__test_nodes:
            logs.info(' Creating test node (name=%s)', n.get('name'))
            Api().nodes_post(identifiers=n)
            rsp = self.__client.last_response
            if rsp.status != 201:
                logs.info(' Failed to create test node')
            # self.assertEqual(201, rsp.status, msg=rsp.reason)

    def delete_temp_nodes(self):
        # utility to delete the set of test nodes
        codes = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        test_names = [t.get('name') for t in self.__test_nodes]
        for n in nodes:
            name = n.get('name')
            if name in test_names:
                uuid = n.get('id')
                logs.info(' Deleting node %s (name=%s)', uuid, name)
                Api().nodes_del_by_id(identifier=uuid)
                rsp = self.__client.last_response
                if rsp.status != 204:
                    codes.append(rsp)
                    logs.info(' Failed to delete node %s - %s', uuid, name)
        return len(codes)

    # @test(groups=['nodes.api2.discovery.test'])
    def test_nodes_discovery(self):
        # API 2.0 Testing Graph.Discovery completion
        self.__discovery_duration = datetime.now()
        logs.info(' Wait start time: %s', str(self.__discovery_duration))
        self.__task = WorkerThread(AMQPWorker(queue=QUEUE_GRAPH_FINISH,
                                              callbacks=[self.handle_graph_finish]), 'discovery')

        def start(worker, id):
            worker.start()

        tasks = WorkerTasks(tasks=[self.__task], func=start)
        tasks.run()
        tasks.wait_for_completion(timeout_sec=1200)
        self.assertFalse(self.__task.timeout,
                         msg=('timeout waiting for task %s', self.__task.id))

    def handle_graph_finish(self, body, message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        Api().workflows_get()
        workflows = self.__get_data()
        for w in workflows:
            injectableName = w.get('injectableName')
            if injectableName == 'Graph.SKU.Discovery':
                graphId = w.get('context', {}).get('graphId', {})
                if graphId == routeId:
                    message.ack()
                    status = body.get('status')
                    if status == 'succeeded' or status == 'failed':
                        duration = datetime.now() - self.__discovery_duration
                        msg = {
                            'graph_name': injectableName,
                            'status': status,
                            'route_id': routeId,
                            'duration': str(duration)
                        }
                        if status == 'failed':
                            msg['active_task'] = w.get('tasks', {})
                            logs.error(json.dumps(msg, indent=4))
                        else:
                            logs.info(json.dumps(msg, indent=4))
                            self.__discovered += 1
                        break
        check = self.check_compute_count()
        if check and check == self.__discovered:
            self.__task.worker.stop()
            self.__task.running = False
            self.__discovered = 0

    # @test(groups=['test-nodes-api2'], depends_on_groups=['nodes.api2.discovery.test'])
    @depends(after='test_nodes_discovery')
    def test_nodes(self):
        # Testing GET:/api/2.0/nodes
        Api().nodes_get_all()
        nodes = self.__get_data()
        logs.debug(json.dumps(nodes, indent=4))
        for node in nodes:
            logs.info(" Node: %s %s %s", node.get('id'), node.get('type'), node.get('name'))
        self.assertNotEqual(0, len(nodes), msg='Node list was empty!')

    # @test(groups=['test-node-id-api2'], depends_on_groups=['test-nodes-api2'])
    @depends(after='test_nodes')
    def test_node_id(self):
        # Testing GET:/api/2.0/nodes/:id
        Api().nodes_get_all()
        nodes = self.__get_data()
        logs.debug(json.dumps(nodes, indent=4))
        codes = []
        for n in nodes:
            logs.info(" Node: %s %s %s", n.get('id'), n.get('type'), n.get('name'))
            logs.debug(json.dumps(n, indent=4))
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Api().nodes_get_by_id(identifier=uuid)
                rsp = self.__client.last_response
                codes.append(rsp)
        self.assertNotEqual(0, len(codes), msg='Failed to find compute node Ids')
        for c in codes:
            self.assertEqual(200, c.status, msg=c.reason)
        self.assertRaises(ApiException, Api().nodes_get_by_id, 'fooey')

    # @test(groups=['create-node-api2'], depends_on_groups=['test-node-id-api2'])
    @depends(after='test_node_id')
    def test_node_create(self):
        # Testing POST:/api/2.0/nodes/
        # This test uses the fake set of nodes __test_nodes
        for n in self.__test_nodes:
            logs.info(' Creating node (name=%s)', n.get('name'))
            Api().nodes_post(identifiers=n)
            rsp = self.__client.last_response
            self.assertEqual(201, rsp.status, msg=rsp.reason)

    # @test(groups=['patch-node-api2'], depends_on_groups=['test-node-id-api2'])
    @depends(after='test_node_create')
    def test_node_patch(self):
        # Testing PATCH:/api/2.0/nodes/:id
        data = {"name": 'fake_name_test'}
        Api().nodes_get_all()
        nodes = self.__get_data()
        codes = []
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                uuid = n.get('id')
                Api().nodes_patch_by_id(identifier=uuid, body=data)
                rsp = self.__client.last_response
                test_nodes = self.__get_data()
                self.assertEqual(test_nodes.get('name'), 'fake_name_test', 'Oops patch failed')
                codes.append(rsp)
                logs.info(' Restoring name to "test_compute_node"')
                correct_data = {"name": 'test_compute_node'}
                Api().nodes_patch_by_id(identifier=uuid, body=correct_data)
                rsp = self.__client.last_response
                restored_nodes = self.__get_data()
                self.assertEqual(restored_nodes.get('name'), 'test_compute_node', 'Oops restoring failed')
                codes.append(rsp)
        self.assertNotEqual(0, len(codes), msg='Failed to find compute node Ids')
        for c in codes:
            self.assertEqual(200, c.status, msg=c.reason)
        self.assertRaises(ApiException, Api().nodes_patch_by_id, 'fooey', data)

    # @test(groups=['delete-node-api2'], depends_on_groups=['patch-node-api2'])
    @depends(after='test_node_patch')
    def test_node_delete(self):
        # Testing DELETE:/api/2.0/nodes/:id
        codes = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        test_names = [t.get('name') for t in self.__test_nodes]
        for n in nodes:
            name = n.get('name')
            if name in test_names:
                uuid = n.get('id')
                logs.info(' Deleting node %s (name=%s)', uuid, name)
                Api().nodes_del_by_id(identifier=uuid)
                codes.append(self.__client.last_response)

        self.assertNotEqual(0, len(codes), msg='Delete node list empty, should contain test nodes!')
        for c in codes:
            self.assertEqual(204, c.status, msg=c.reason)
        self.assertRaises(ApiException, Api().nodes_del_by_id, 'fooey')

    # @test(groups=['catalog_nodes-api2'], depends_on_groups=['delete-node-api2'])
    @depends(after='test_node_delete')
    def test_node_catalogs(self):
        # Testing GET:/api/2.0/nodes/:id/catalogs
        resps = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().nodes_get_catalog_by_id(identifier=n.get('id'))
                resps.append(self.__get_data())
        for resp in resps:
            self.assertNotEqual(0, len(resp), msg='Node catalog is empty!')
        self.assertRaises(ApiException, Api().nodes_get_catalog_by_id, 'fooey')

    # @test(groups=['catalog_source-api2'], depends_on_groups=['catalog_nodes-api2'])
    @depends(after='test_node_catalogs')
    def test_node_catalogs_bysource(self):
        # Testing GET:/api/2.0/nodes/:id/catalogs/source
        resps = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().nodes_get_catalog_source_by_id(identifier=n.get('id'), source='bmc')
                resps.append(self.__client.last_response)
        for resp in resps:
            self.assertEqual(200, resp.status, msg=resp.reason)
        self.assertRaises(ApiException, Api().nodes_get_catalog_source_by_id, 'fooey', 'bmc')

    # @test(groups=['node_workflows-api2'], depends_on_groups=['catalog_source-api2'])
    @depends(after='test_node_catalogs_bysource')
    def test_node_workflows_get(self):
        # Testing GET:/api/2.0/nodes/:id/workflows
        resps = []
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().nodes_get_workflow_by_id(identifier=n.get('id'))
                resps.append(self.__get_data())
        for resp in resps:
            self.assertNotEqual(0, len(resp), msg='No Workflows found for Node')

    # @test(groups=['node_tags_patch'], depends_on_groups=['node_workflows_del_active-api2'])
    # @depends(after='test_workflows_action')
    @depends(after='test_node_workflows_get')
    def test_node_tags_patch(self):
        # Testing PATCH:/api/2.0/nodes/:id/tags
        codes = []
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        codes.append(rsp)
        for n in nodes:
            logs.info(' node to tag %s', n.get('id'))
            logs.debug(json.dumps(n, indent=4))
            Api().nodes_patch_tag_by_id(identifier=n.get('id'), body=self.__test_tags)
            logs.info(' Creating tag (name=%s)', self.__test_tags)
            rsp = self.__client.last_response
            codes.append(rsp)
        for c in codes:
            self.assertEqual(200, c.status, msg=c.reason)
        self.assertRaises(ApiException, Api().nodes_patch_tag_by_id, 'fooey', body=self.__test_tags)

    # @test(groups=['node_tags_get'], depends_on_groups=['node_tags_patch'])
    @depends(after='test_node_tags_patch')
    def test_node_tags_get(self):
        # Testing GET:api/2.0/nodes/:id/tags
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
                self.assertTrue(t in tags, msg="cannot find new tag")
        for c in codes:
            self.assertEqual(200, c.status, msg=c.reason)
        self.assertRaises(ApiException, Api().nodes_patch_tag_by_id, 'fooey', body=self.__test_tags)

    # @test(groups=['node_tags_delete'], depends_on_groups=['node_tags_get'])
    @depends(after='test_node_tags_get')
    def test_node_tags_del(self):
        # Testing DELETE:api/2.0/nodes/:id/tags/:tagName
        # This workflow deletes the the tags off the nodes created by
        # the test above test_node_tags_patch
        get_codes = []
        del_codes = []
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        get_codes.append(rsp)
        for n in nodes:
            for t in self.__test_tags.get('tags'):
                Api().nodes_del_tag_by_id(identifier=n.get('id'), tag_name=t)
                rsp = self.__client.last_response
                del_codes.append(rsp)
            Api().nodes_get_by_id(identifier=n.get('id'))
            rsp = self.__client.last_response
            get_codes.append(rsp)
            updated_node = loads(rsp.data)
            for t in self.__test_tags.get('tags'):
                self.assertTrue(t not in updated_node.get('tags'), msg="Tag " + t + " was not deleted")
        for c in get_codes:
            self.assertEqual(200, c.status, msg=c.reason)
        for c in del_codes:
            self.assertEqual(204, c.status, msg=c.reason)
        self.assertRaises(ApiException, Api().nodes_del_tag_by_id, 'fooey', tag_name=['tag'])

    # @test(groups=['nodes_tag_masterDelete'], depends_on_groups=['node_tags_delete'])
    @depends(after='test_node_tags_del')
    def test_node_tags_masterDel(self):
        # Testing DELETE:api/2.0/nodes/tags/:tagName
        # negative test:  This workflow calls the test_node_tags_patch test above to
        # get tags put back on the nodes, then verifies trying to delete an non-existing
        # tag id doesn't cause a failure, then it deletes all the tags that were created
        codes = []
        self.test_node_tags_patch()
        t = 'tag3'
        logs.info(" Check to make sure invalid tag is not deleted")
        Api().nodes_master_del_tag_by_id(tag_name=t)
        rsp = self.__client.last_response
        codes.append(rsp)
        logs.info(" Test to check valid tags are deleted")
        for t in self.__test_tags.get('tags'):
            Api().nodes_master_del_tag_by_id(tag_name=t)
            rsp = self.__client.last_response
            codes.append(rsp)
        for c in codes:
            self.assertEqual(204, c.status, msg=c.reason)

    # @test(groups=['node_put_obm_by_node_id'], depends_on_groups=['nodes_tag_masterDelete'])
    @depends(after='test_node_tags_masterDel')
    def test_node_put_obm_by_node_id(self):
        # Testing PUT:/api/2.0/nodes/:id/obm
        self.create_temp_nodes()
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        self.assertEqual(200, rsp.status, msg=rsp.status)
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                logs.info(" Node to put obm: %s %s ", n.get('id'), n.get('name'))
                self.__test_obm["nodeId"] = str(n.get('id'))
                logs.debug(json.dumps(n, indent=4))
                Api().nodes_put_obms_by_node_id(identifier=n.get('id'), body=self.__test_obm)
                logs.info(' Creating obm: %s ', str(self.__test_obm))
                rsp = self.__client.last_response
                self.assertEqual(201, rsp.status, msg=rsp.status)

    # @test(groups=['node_get_obm_by_node_id'], depends_on_groups=['node_put_obm_by_node_id'])
    @depends(after='test_node_put_obm_by_node_id')
    def test_node_get_obm_by_node_id(self):
        # Testing GET:/api/2.0/:id/obm
        # FIX ME 12/21/16: This test deletes all OBM settings on the nodes
        # If run before any other testing that relies on OBMs being set, you've messed
        # up your test bed.  Restore the OBMS when this set is done or run against __test_nodes
        # Or check somehow if we are only running against virtual nodes
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        self.assertEqual(200, rsp.status, msg=rsp.status)
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                logs.debug(json.dumps(n, indent=4))
                Api().nodes_get_obms_by_node_id(identifier=n.get('id'))
                logs.info(' getting OBMs for node: %s', n.get('id'))
                rsp = self.__client.last_response
                self.assertEqual(200, rsp.status, msg=rsp.status)
                obms = loads(rsp.data)
                self.assertNotEqual(0, len(obms), msg='OBMs list was empty!')
                for obm in obms:
                    id = obm.get('id')
                    Api().obms_delete_by_id(identifier=id)
                    rsp = self.__client.last_response
                    self.assertEqual(204, rsp.status, msg=rsp.status)

    # @test(groups=['node_put_obm_invalid'], depends_on_groups=['node_get_obm_by_node_id'])
    @depends(after='test_node_get_obm_by_node_id')
    def test_node_put_obm_invalid_node_id(self):
        # Testing that PUT:/api/2.0/:id/obm returns 404 with invalid node ID
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        self.assertEqual(200, rsp.status, msg=rsp.status)
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                try:
                    Api().nodes_put_obms_by_node_id(identifier='invalid_ID', body=self.__test_obm)
                    self.fail(msg='did not raise exception')
                except ApiException as e:
                    self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))

    # @test(groups=['node_get_obm_invalid'], depends_on_groups=['node_put_obm_invalid'])
    @depends(after='test_node_put_obm_invalid_node_id')
    def test_node_get_obm_invalid_node_id(self):
        # Testing that PUT:/api/2.0/:id/obm returns 404 with invalid node ID
        Api().nodes_get_all()
        rsp = self.__client.last_response
        nodes = loads(rsp.data)
        self.assertEqual(200, rsp.status, msg=rsp.status)
        for n in nodes:
            if n.get('name') == 'test_compute_node':
                try:
                    Api().nodes_get_obms_by_node_id(identifier='invalid_ID')
                    self.fail(msg='did not raise exception')
                except ApiException as e:
                    self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))

    @depends(after='test_node_get_obm_invalid_node_id')
    def test_clean_up_test_nodes(self):
        # Clean up the added test nodes
        self.assertEqual(0, self.delete_temp_nodes(), msg="Failed to clean up test nodes from script")
