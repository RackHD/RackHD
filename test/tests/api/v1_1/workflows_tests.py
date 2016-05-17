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
        self.__graphName = None
        self.__graphId = None
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

    def put_workflow(self, workflowDict):
        #adding/updating  a workflow task
        LOG.info ("Adding workflow task : " +  str(workflowDict))
        Workflows().workflows_put(body=workflowDict)
        resp= self.__client.last_response
        assert_equal(200,resp.status)

        #Validating the content is as expected
        Workflows().workflows_library_injectable_name_get('*')
        rawj=  json.loads(self.__client.last_response.data)
        foundInsertedWorkflow = False
        for i, var  in enumerate (rawj):
            if ( workflowDict['injectableName'] ==  str (rawj[i].get('injectableName')) ):
                foundInsertedWorkflow = True
                readWorkflowTask= rawj[i]
                readFriendlyName= readWorkflowTask.get('friendlyName')
                readInjectableName  = readWorkflowTask.get('injectableName')
                assert_equal(readFriendlyName,workflowDict.get('friendlyName'))
                assert_equal(readInjectableName,workflowDict.get('injectableName'))

        assert_equal(foundInsertedWorkflow, True)

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

        self.put_workflow(self.workflowDict)

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
        self.__graphName = graph_name

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
                    assert_equal(404, e.status, message = 'status should be 404')

                # Verify the active workflow has been deleted
                # If the post workflow API was called immediatly after deleting active workflow,
                # the API would fail at the first time and retry, though actually the workflow was issued twice
                # in a consecutive manner, which would bring malfunction of vBMC
                retries = 5
                Nodes().nodes_identifier_workflows_active_get(id)
                status = self.__client.last_response.status
                while status != 204 and retries != 0:
                    LOG.warning('Workflow status for Node {0} (status={1},retries={2})'.format(id,status,retries))
                    sleep(1)
                    retries -= 1
                    Nodes().nodes_identifier_workflows_active_get(id)
                    status = self.__client.last_response.status

                assert_equal(204, status, message = 'status should be 204')

                Nodes().nodes_identifier_workflows_post(id,name=graph_name,body={})
                data = loads(self.__client.last_response.data)
                self.__graphId = data["context"]['graphId']
                self.__task_worker.start()

    def handle_graph_finish(self,body,message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        assert_not_equal(routeId,None)
        message.ack()
        if self.__graphId == routeId:
            # Get workflow information
            Workflows().workflows_instance_id_get(self.__graphId)
            data = loads(self.__client.last_response.data)
            nodeid = data['context']['target']
            injectableName = data['definition']['injectableName']

            status = body['status']
            msg = '{0} - target: {1}, status: {2}, route: {3}'.format(injectableName,nodeid,status,routeId)
            if status == 'succeeded':
                LOG.info(msg)
            assert_equal(status, 'succeeded', msg);
            self.__task_worker.stop()

    @test(groups=['test_node_workflows_post'], \
            depends_on_groups=['workflows_put', 'delete_all_active_workflows'])
    def test_node_workflows_post(self):
        """Testing node POST:id/workflows"""
        self.post_workflows("Graph.noop-example")
