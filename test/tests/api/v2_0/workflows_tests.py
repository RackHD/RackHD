import json
from config.api2_0_config import *
from config.amqp import *
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from modules.logger import Log
from modules.amqp import AMQPWorker
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads
import time


LOG = Log(__name__)

@test(groups=['workflows_api2.tests'])
class WorkflowsTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__task_worker = None
        self.workflowDict = {
            "friendlyName": "Shell Commands Hwtest_1",
            "injectableName": "Graph.post.test",
            "tasks": [{"taskName": "Task.Trigger.Send.Finish"}]
        }
        self.workflowDict2 = {
            "friendlyName": "Shell Commands Hwtest_2",
            "injectableName": "Graph.post.test",
            "tasks": [{"taskName": "Task.Trigger.Send.Finish"}]
        }

    @test(groups=['delete_all_active_workflows_api2'])
    def delete_all_active_workflows(self):
        """Testing node DELETE:/nodes/identifier/workflows/active"""
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        for node in nodes:
            if node.get('type') == 'compute':
                id = node.get('id')
                assert_not_equal(id,None)
                try:
                    Api().nodes_del_active_workflow_by_id(id)
                except rest.ApiException as err:
                    LOG.warning(err)

    @test(groups=['workflows_get_api2'], depends_on_groups=['delete_all_active_workflows_api2'])
    def test_workflows_get(self):
        """ Testing GET:/workflows"""
        Api().workflows_get()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)),
                         message='Active workflows list was empty!')

    @test(groups=['workflows_post_api2'], depends_on_groups=['delete_all_active_workflows_api2'])
    def test_workflows_post(self):
        """Testing POST:/workflows"""
        Api().workflows_post(body={"name": 'Graph.noop-example'})
        assert_equal(201, self.__client.last_response.status)
        rawj = json.loads(self.__client.last_response.data)
        instance_id = rawj.get('instanceId')
        assert_is_not_none(instance_id)
        assert_equal('Graph.noop-example', str(rawj['definition'].get('injectableName')))

    @test(groups=['workflows_get_id_api2'], depends_on_groups=['workflows_get_api2'])
    def test_workflows_id_get(self):
        """ Testing GET:/workflows/identifier"""

        # Getting the identifier of the first workflow in order to validate the get-id function
        Api().workflows_get()
        rawj = json.loads(self.__client.last_response.data)
        instance_id = rawj[0].get('id')
        assert_is_not_none(instance_id)
        Api().workflows_get_by_id(instance_id)
        assert_equal(200,self.__client.last_response.status)

    @test(groups=['workflows_get_id_api2'],depends_on_groups=['workflows_get_api2'])
    def test_negative_workflows_id_get(self):
        """ Negative Testing GET:/workflows/identifier"""
        try:
            Api().workflows_get_by_id("WrongIdentifier")
        except Exception,e:
            assert_equal(404,e.status, message = 'status should be 404')

    @test(groups=['test_workflows_graphs_get_api2'])
    def test_workflows_graphs_get(self):
        """Testing GET:/workflows/graphs"""
        Api().workflows_get_graphs()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)),
                         message='Workflows list was empty!')

    @test(groups=['workflows_graphs_put_api2'])
    def test_workflows_graphs_put(self):
        """ Testing PUT:/workflows/graphs """

        # Make sure there is no workflowTask with the same name
        Api().workflows_get_graphs_by_name('*')
        rawj = json.loads(self.__client.last_response.data)

        for i, var in enumerate(rawj):
            if self.workflowDict['injectableName'] == str(rawj[i].get('injectableName')):
                fnameList = str(rawj[i].get('friendlyName')).split('_')
                suffix = int(fnameList[1]) + 1
                self.workflowDict['friendlyName'] = fnameList[0] + '_' + str(suffix)
                break

        # Add a workflow task
        LOG.info ("Adding workflow task : " + str(self.workflowDict))
        Api().workflows_put_graphs(body=self.workflowDict)
        resp = self.__client.last_response
        assert_equal(201,resp.status)

        # Validate the content
        Api().workflows_get_graphs()
        rawj = json.loads(self.__client.last_response.data)
        foundInsertedWorkflow = False
        for i, var in enumerate(rawj):
            if self.workflowDict['injectableName'] == str(rawj[i].get('injectableName')):
                foundInsertedWorkflow = True
                readWorkflowTask = rawj[i]
                readFriendlyName = readWorkflowTask.get('friendlyName')
                readInjectableName = readWorkflowTask.get('injectableName')
                assert_equal(readFriendlyName,self.workflowDict.get('friendlyName'))
                assert_equal(readInjectableName,self.workflowDict.get('injectableName'))

        assert_equal(foundInsertedWorkflow, True)

    @test(groups=['workflows_graphs_get_name_api2'],
          depends_on_groups=['workflows_graphs_put_api2'])
    def test_workflows_library_id_get(self):
        """ Testing GET:/workflows/graphs/injectableName"""
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        assert_equal(200,self.__client.last_response.status)
        rawj = json.loads(self.__client.last_response.data)
        assert_equal(self.workflowDict.get('friendlyName'), str(rawj[0].get('friendlyName')))

    @test(groups=['test_workflows_graphs_put_name_api2'],
          depends_on_groups=['workflows_graphs_get_name_api2'])
    def test_workflows_graphs_name_put(self):
        """Testing PUT:/workflows/graphs"""
        # Test updating a graph
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = json.loads(self.__client.last_response.data)
        assert_equal(self.workflowDict.get('friendlyName'), str(rawj[0].get('friendlyName')))
        Api().workflows_put_graphs(body=self.workflowDict2)
        assert_equal(201,self.__client.last_response.status)
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = json.loads(self.__client.last_response.data)
        assert_equal(self.workflowDict2.get('friendlyName'), str(rawj[0].get('friendlyName')))

    @test(groups=['test_workflows_graphs_delete_name_api2'],
          depends_on_groups=['test_workflows_graphs_put_name_api2'])
    def test_workflows_graphs_delete(self):
        """Testing DELETE:/workflows/graphs/injectableName"""
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = json.loads(self.__client.last_response.data)
        assert_equal(self.workflowDict2.get('friendlyName'), str(rawj[0].get('friendlyName')))
        Api().workflows_delete_graphs_by_name(self.workflowDict.get('injectableName'))
        assert_equal(200,self.__client.last_response.status)
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        assert_equal(0, len(json.loads(self.__client.last_response.data)))

    @test(groups=['test_node_workflows_post_api2'],
            depends_on_groups=['workflows_graphs_put_api2', 'delete_all_active_workflows_api2'])
    def test_node_workflows_post(self):
        """Testing POST:/nodes/id/workflows"""
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)

        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                assert_not_equal(id,None)
                LOG.info('starting amqp listener for node {0}'.format(id))
                self.__task_worker = AMQPWorker(queue=QUEUE_GRAPH_FINISH,
                                    callbacks=[self.handle_graph_finish])
                try:
                    Api().nodes_del_active_workflow_by_id(id)
                except Exception,e:
                    assert_equal(404,e.status, message='status should be 404')
                Api().nodes_post_workflow_by_id(id, name='Graph.noop-example', body={})
                self.__task_worker.start()

    def handle_graph_finish(self,body,message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        assert_not_equal(routeId,None)
        Api().workflows_get()
        workflows = loads(self.__client.last_response.data)
        message.ack()
        for w in workflows:
            injectableName = w['definition'].get('injectableName')
            if injectableName == 'Graph.noop-example':
                graphId = w['context'].get('graphId')
                if graphId == routeId:
                    if 'target' in w['context']:
                        nodeid = w['context']['target'] or 'none'
                    else:
                        nodeid = 'none'
                    status = body['status']
                    if status == 'succeeded':
                        LOG.info('{0} - target: {1}, status: {2}, route: {3}'.
                                 format(injectableName,nodeid,status,routeId))
                        self.__task_worker.stop()
                        break

