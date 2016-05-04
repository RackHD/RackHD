import json
from config.api1_1_config import *
from config.amqp import *
from on_http_api1_1 import WorkflowApi as Workflows
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import rest
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

@test(groups=['workflows.tests'])
class WorkflowsTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__task_worker = None
        self.__graph_name = None
        self.workflowDict = {
            "friendlyName": "Shell Commands Hwtest_1",
            "injectableName": "Graph.post.test",
            "tasks": [{"taskName": "Task.Trigger.Send.Finish"}]
        }

    @test(groups=['delete_all_active_workflows'])
    def delete_all_active_workflows(self):
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        for node in nodes:
            if node.get('type') == 'compute':
                id = node.get('id')
                assert_not_equal(id,None)
                try:
                    Nodes().nodes_identifier_workflows_active_delete(id)
                except rest.ApiException as err:
                    LOG.warning(err)

    @test(groups=['workflows_get'], \
            depends_on_groups=['delete_all_active_workflows'])
    def test_workflows_get(self):
        """ Testing GET:/"""
        Workflows().workflows_get()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)), message='Active workflows list was empty!')

    @test(groups=['workflows_get_id'],depends_on_groups=['workflows_get'])
    def test_workflows_id_get(self):
        """ Testing GET:/identifier"""
        # Getting the identifier of the first workflow in order to validate the get-id function
        Workflows().workflows_get()
        rawj = json.loads(self.__client.last_response.data)
        instance_id = rawj[0].get('instanceId')
        assert_is_not_none(instance_id)
        Workflows().workflows_instance_id_get(instance_id)
        assert_equal(200,self.__client.last_response.status)

    @test(groups=['workflows_get_id'],depends_on_groups=['workflows_get'])
    def test_negative_workflows_id_get(self):
        """ Negative Testing GET:/identifier"""
        try:
            Workflows().nodes_identifier_workflows_get("WrongIdentifier")
        except Exception,e:
            assert_equal(404,e.status, message = 'status should be 404')

    @test(groups=['workflows_put'], depends_on_groups=['workflows_library_get'])
    def test_workflows_put(self):
        """ Testing PUT:/workflows:/library """

        #Making sure that there is no workflowTask with the same name from previous test runs
        Workflows().workflows_library_injectable_name_get('*')
        rawj =  json.loads(self.__client.last_response.data)

        for i, var  in enumerate (rawj):
            if ( self.workflowDict['injectableName'] ==  str (rawj[i].get('injectableName')) ):
                fnameList = str (rawj[i].get('friendlyName')).split('_')
                suffix= int (fnameList[1]) + 1
                self.workflowDict['friendlyName']= fnameList[0]+ '_' + str(suffix)
                break

        #adding/updating  a workflow task
        LOG.info ("Adding workflow task : " +  str(self.workflowDict))
        Workflows().workflows_put(body=self.workflowDict)
        resp= self.__client.last_response
        assert_equal(200,resp.status)

        #Validating the content is as expected
        Workflows().workflows_library_injectable_name_get('*')
        rawj=  json.loads(self.__client.last_response.data)
        foundInsertedWorkflow = False
        for i, var  in enumerate (rawj):
            if ( self.workflowDict['injectableName'] ==  str (rawj[i].get('injectableName')) ):
                foundInsertedWorkflow = True
                readWorkflowTask= rawj[i]
                readFriendlyName= readWorkflowTask.get('friendlyName')
                readInjectableName  = readWorkflowTask.get('injectableName')
                assert_equal(readFriendlyName,self.workflowDict.get('friendlyName'))
                assert_equal(readInjectableName,self.workflowDict.get('injectableName'))


        assert_equal(foundInsertedWorkflow, True)

    @test(groups=['workflows_library_identifier_get'], \
            depends_on_groups=['workflows_put'])
    def test_workflows_library_identifier_get(self):
        """ Testing GET:/library:/identifier"""
        Workflows().workflows_library_injectable_name_get(self.workflowDict.get('injectableName'))
        assert_equal(200,self.__client.last_response.status)
        assert_equal(self.workflowDict.get('friendlyName'),str(json.loads(self.__client.last_response.data).get('friendlyName')))

    def post_workflows(self, graph_name):
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        self.__graph_name = graph_name

        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                assert_not_equal(id,None)
                LOG.info('starting amqp listener for node {0}'.format(id))
                self.__task_worker=AMQPWorker(queue=QUEUE_GRAPH_FINISH,
                                    callbacks=[self.handle_graph_finish])
                try:
                    Nodes().nodes_identifier_workflows_active_delete(id)
                except Exception,e:
                    assert_equal(404,e.status, message = 'status should be 404')
                Nodes().nodes_identifier_workflows_post(id,name=graph_name,body={})
                self.__task_worker.start()

    def handle_graph_finish(self,body,message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        assert_not_equal(routeId,None)
        Workflows().workflows_get()
        workflows = loads(self.__client.last_response.data)
        message.ack()
        for w in workflows:
            injectableName = w['definition'].get('injectableName')
            if injectableName == self.__graph_name:
                graphId = w['context'].get('graphId')
                if graphId == routeId:
                    nodeid = w['context']['target']
                    status = body['status']
                    if status == 'succeeded':
                        LOG.info('{0} - target: {1}, status: {2}, route: {3}'.format(injectableName,nodeid,status,routeId))
                        self.__task_worker.stop()
                        break

    @test(groups=['test_node_workflows_post'], \
            depends_on_groups=['workflows_put', 'delete_all_active_workflows'])
    def test_node_workflows_post(self):
        """Testing node POST:id/workflows"""
        self.post_workflows("Graph.noop-example")
