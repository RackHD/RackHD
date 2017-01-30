import json
from config.api1_1_config import *
from config.amqp import *
from on_http_api1_1 import WorkflowApi as Workflows
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import rest
from on_http_api1_1.rest import ApiException
from modules.logger import Log
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
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
from json import dumps, loads
import time

LOG = Log(__name__)

HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND  = 404

@test(groups=['workflows.tests'])
class WorkflowsTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__task_worker = None
        self.__graph_name = None
        self.__tasks = []
        self.__graph_status = []
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
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)), \
            message='Active workflows list was empty!')

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
        except ApiException as e:
            assert_equal(HTTP_NOT_FOUND, e.status, \
                message = 'status should be {0}'.format(HTTP_NOT_FOUND))
        except (TypeError, ValueError) as e:
            assert(e.message);

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
        assert_equal(self.workflowDict.get('friendlyName'), \
            str(json.loads(self.__client.last_response.data).get('friendlyName')))

    def post_workflows(self, graph_name, \
                       timeout_sec=300, nodes=[], data={}, \
                       tasks=[], callback=None, run_now=True):
        self.__graph_name = graph_name
        self.__graph_status = []
        
        if len(nodes) == 0:
            Nodes().nodes_get()
            for n in loads(self.__client.last_response.data):
                if n.get('type') == 'compute':
                    nodes.append(n.get('id'))
        
        if callback == None:
            callback = self.handle_graph_finish
        
        for node in nodes:
            LOG.info('Starting AMQP listener for node {0}'.format(node))
            worker = AMQPWorker(queue=QUEUE_GRAPH_FINISH, callbacks=[callback])
            thread = WorkerThread(worker, node)
            self.__tasks.append(thread)
            tasks.append(thread)
            
            try:
                Nodes().nodes_identifier_workflows_active_delete(node)
            except ApiException as e:
                assert_equal(HTTP_NOT_FOUND, e.status, \
                    message = 'status should be {0}'.format(HTTP_NOT_FOUND))
            except (TypeError, ValueError) as e:
                assert(e.message)

            retries = 5
            Nodes().nodes_identifier_workflows_active_get(node)
            status = self.__client.last_response.status
            while status != HTTP_NO_CONTENT and retries != 0:
                status = self.__client.last_response.status
                LOG.warning('Workflow status for Node {0} (status={1},retries={2})' \
                    .format(node, status, retries))
                time.sleep(1)
                retries -= 1
                Nodes().nodes_identifier_workflows_active_get(node)
            assert_equal(HTTP_NO_CONTENT, status, \
                message = 'status should be {0}'.format(HTTP_NO_CONTENT))
            Nodes().nodes_identifier_workflows_post(node, name=graph_name, body=data)
        if run_now:
            self.run_workflow_tasks(self.__tasks, timeout_sec)
            
    def post_unbound_workflow(self, graph_name, \
                       timeout_sec=300, data={}, \
                       tasks=[], callback=None, run_now=True):
        self.__graph_name = graph_name
        self.__graph_status = []
        
        if callback == None:
            callback = self.handle_graph_finish
        
        LOG.info('Starting AMQP listener for {0}'.format(self.__graph_name))
        worker = AMQPWorker(queue=QUEUE_GRAPH_FINISH, callbacks=[callback])
        thread = WorkerThread(worker, self.__graph_name)
        self.__tasks.append(thread)
        tasks.append(thread)
        Workflows().workflows_post(graph_name, body=data)
        if run_now:
            self.run_workflow_tasks(self.__tasks, timeout_sec)
            
    def run_workflow_tasks(self, tasks, timeout_sec):
        def thread_func(worker, id):
            worker.start()
        tasks = self.__tasks if tasks is None else tasks
        worker_tasks = WorkerTasks(tasks=self.__tasks, func=thread_func)
        worker_tasks.run()
        worker_tasks.wait_for_completion(timeout_sec=timeout_sec)
        for task in tasks:
            if task.timeout: 
                LOG.error('Timeout for {0}, node {1}'.format(self.__graph_name, task.id))
                self.__graph_status.append('failed')
        if 'failed' in self.__graph_status:
            fail('Failure running {0}'.format(self.__graph_name))

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
                    nodeid = w['context'].get('target', injectableName)
                    status = body['status']
                    if status == 'succeeded' or status == 'failed':
                        self.__graph_status.append(status)
                        for task in self.__tasks:
                            if task.id == nodeid:
                                task.worker.stop()
                                task.running = False
                        msg = {
                            'graph_name': injectableName,
                            'target': nodeid,
                            'status': status,
                            'route_id': routeId
                        }
                        if status == 'failed':
                            msg['active_task'] = w['tasks']
                            LOG.error(msg, json=True)
                        else:
                            LOG.info(msg, json=True)
                        break
        
    @test(groups=['test_node_workflows_post'], \
            depends_on_groups=['workflows_put', 'delete_all_active_workflows'])
    def test_node_workflows_post(self):
        """Testing node POST:id/workflows"""
        self.post_workflows("Graph.noop-example")
