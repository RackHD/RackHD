'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from config.amqp import QUEUE_GRAPH_FINISH
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
from json import loads, dumps
from nose.plugins.attrib import attr
from nosedep import depends

logs = flogging.get_loggers()

HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND = 404


@attr(regression=False, smoke=True, workflows_api2_tests=True)
class WorkflowsTests(fit_common.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        # cls.__task_worker = None
        cls.__graph_name = None
        cls.__tasks = []
        cls.__graph_status = []
        cls.workflowDict = {
            "friendlyName": "Shell Commands API 2.0 Hwtest_1",
            "injectableName": "Graph.post.test.api2",
            "tasks": [
                {
                    "taskName": "Task.Trigger.Send.Finish",
                    "label": "Task.Trigger"
                }
            ]
        }
        cls.workflowDict2 = {
            "friendlyName": "Shell Commands API 2.0 Hwtest_2",
            "injectableName": "Graph.post.test.api2",
            "tasks": [
                {
                    "taskName": "Task.Trigger.Send.Finish",
                    "label": "Task.Trigger"
                }
            ]
        }

    def test_delete_all_active_workflows(self):
        # """Testing node PUT:/nodes/identifier/workflows/action"""
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        for node in nodes:
            if node.get('type') == 'compute':
                id = node.get('id')
                self.assertNotEqual(id, None)
                try:
                    Api().nodes_workflow_action_by_id(id, {'command': 'cancel'})
                except ApiException as err:
                    logs.warning(" Error: %s", err)

    @depends(after='test_delete_all_active_workflows')
    def test_workflows_get(self):
        # """ Testing GET:/workflows"""
        Api().workflows_get()
        self.assertEqual(200, self.__client.last_response.status)
        self.assertNotEqual(0, len(loads(self.__client.last_response.data)),
                            msg='Active workflows list was empty!')

    @depends(after='test_workflows_get')
    def test_workflows_post(self):
        # """Testing POST:/workflows"""
        Api().workflows_post(body={"name": 'Graph.noop-example'})
        self.assertEqual(201, self.__client.last_response.status)
        rawj = loads(self.__client.last_response.data)
        instance_id = rawj.get('instanceId')
        self.assertIsNotNone(instance_id)
        self.assertEqual('Graph.noop-example', str(rawj['definition'].get('injectableName')))

    @depends(after='test_workflows_get')
    def test_workflows_id_get(self):
        # """ Testing GET:/workflows/identifier"""

        # Getting the identifier of the first workflow in order to validate the get-id function
        Api().workflows_get()
        rawj = loads(self.__client.last_response.data)
        instance_id = rawj[0].get('instanceId')
        self.assertIsNotNone(instance_id)
        Api().workflows_get_by_instance_id(instance_id)
        self.assertEqual(200, self.__client.last_response.status)

    @depends(after='test_workflows_get')
    def test_negative_workflows_id_get(self):
        # """ Negative Testing GET:/workflows/identifier"""
        try:
            Api().workflows_get_by_instance_id("WrongIdentifier")
            self.assertEqual(404, self.__client.last_response.status, msg='status should be 404. No exception raised')
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))
        except (TypeError, ValueError) as e:
            assert(e.message)

    def test_workflows_graphs_get(self):
        # """Testing GET:/workflows/graphs"""
        Api().workflows_get_graphs()
        self.assertEqual(200, self.__client.last_response.status)
        resp = loads(self.__client.last_response.data)
        logs.debug_6(" Workflow graphs: %s", dumps(resp, indent=4))
        self.assertNotEqual(0, len(loads(self.__client.last_response.data)),
                            msg='Workflows list was empty!')

    def test_workflows_graphs_put(self):
        # """ Testing PUT:/workflows/graphs """

        # Make sure there is no workflowTask with the same name
        Api().workflows_get_graphs_by_name('*')
        rawj = loads(self.__client.last_response.data)

        for i, var in enumerate(rawj):
            if self.workflowDict['injectableName'] == str(rawj[i].get('injectableName')):
                fnameList = str(rawj[i].get('friendlyName')).split('_')
                suffix = int(fnameList[1]) + 1
                self.workflowDict['friendlyName'] = fnameList[0] + '_' + str(suffix)
                break

        # Add a workflow task
        logs.info("Adding workflow task: %s ", str(self.workflowDict))
        Api().workflows_put_graphs(body=self.workflowDict)
        resp = self.__client.last_response
        self.assertEqual(201, resp.status)

        # Validate the content
        Api().workflows_get_graphs()
        rawj = loads(self.__client.last_response.data)
        foundInsertedWorkflow = False
        for i, var in enumerate(rawj):
            if self.workflowDict['injectableName'] == str(rawj[i].get('injectableName')):
                foundInsertedWorkflow = True
                readWorkflowTask = rawj[i]
                readFriendlyName = readWorkflowTask.get('friendlyName')
                readInjectableName = readWorkflowTask.get('injectableName')
                self.assertEqual(readFriendlyName, self.workflowDict.get('friendlyName'))
                self.assertEqual(readInjectableName, self.workflowDict.get('injectableName'))

        self.assertEqual(foundInsertedWorkflow, True)

    @depends(after='test_workflows_graphs_put')
    def test_workflows_library_id_get(self):
        # """ Testing GET:/workflows/graphs/injectableName"""
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        self.assertEqual(200, self.__client.last_response.status)
        rawj = loads(self.__client.last_response.data)
        self.assertEqual(self.workflowDict.get('friendlyName'), str(rawj[0].get('friendlyName')))

    @depends(after='test_workflows_library_id_get')
    def test_workflows_graphs_name_put(self):
        # """Testing PUT:/workflows/graphs"""
        # Test updating a graph
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = loads(self.__client.last_response.data)
        self.assertEqual(self.workflowDict.get('friendlyName'), str(rawj[0].get('friendlyName')))
        Api().workflows_put_graphs(body=self.workflowDict2)
        self.assertEqual(201, self.__client.last_response.status)
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = loads(self.__client.last_response.data)
        self.assertEqual(self.workflowDict2.get('friendlyName'), str(rawj[0].get('friendlyName')))

    @depends(after='test_workflows_graphs_name_put')
    def test_workflows_graphs_delete(self):
        # """Testing DELETE:/workflows/graphs/injectableName"""
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = loads(self.__client.last_response.data)
        self.assertEqual(self.workflowDict2.get('friendlyName'), str(rawj[0].get('friendlyName')))
        Api().workflows_delete_graphs_by_name(self.workflowDict.get('injectableName'))
        self.assertEqual(204, self.__client.last_response.status)
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        self.assertEqual(0, len(loads(self.__client.last_response.data)))

    def post_workflows(self, graph_name, timeout_sec=10, nodes=[], data=None, tasks=None, callback=None, run_now=True):
        self.__class__.__graph_name = graph_name
        self.__class__.__graph_status = []

        # clean up the defaults
        tasks = tasks if tasks else []
        data = data if data else {}

        if len(nodes) == 0:
            Api().nodes_get_all()
            nodes = loads(self.__client.last_response.data)

        if callback is None:
            logs.info("handle graph finish")
            callback = self.handle_graph_finish

        for n in nodes:
            if n.get('type') == 'compute':
                logs.debug("node is compute")
                id = n.get('id')
                self.assertIsNotNone(id)
                logs.debug(' Starting amqp listener for node %s', id)
                worker = AMQPWorker(queue=QUEUE_GRAPH_FINISH, callbacks=[callback])
                thread = WorkerThread(worker, id)
                self.__class__.__tasks.append(thread)
                tasks.append(thread)
                try:
                    Api().nodes_workflow_action_by_id(id, {'command': 'cancel'})
                except ApiException as e:
                    self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))
                except (TypeError, ValueError) as e:
                    assert(e.message)
                Api().nodes_post_workflow_by_id(id, name=self.__class__.__graph_name, body=data)
                logs.info("Posted workflow %s on node %s", self.__class__.__graph_name, id)

        if run_now:
            logs.info("running workflow tasks....")
            self.run_workflow_tasks(self.__class__.__tasks, timeout_sec)

    def handle_graph_finish(self, body, message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        self.assertIsNotNone(routeId)
        Api().workflows_get()
        workflows = loads(self.__client.last_response.data)
        message.ack()
        for w in workflows:
            injectableName = w['injectableName']
            if injectableName == self.__class__.__graph_name:
                graphId = w['context'].get('graphId')
                if graphId == routeId:
                    if 'target' in w['context']:
                        nodeid = w['context']['target'] or 'none'
                    else:
                        nodeid = 'none'
                    status = body['status']
                    if status == 'succeeded' or status == 'failed':
                        logs.info('%s - target: %s, status: %s, route: %s',
                                  injectableName, nodeid, status, routeId)
                        self.__class__.__graph_status.append(status)

                        for task in self.__class__.__tasks:
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
                            logs.error(dumps(msg, indent=4))
                        else:
                            logs.info(dumps(msg, indent=4))
                        break

    def run_workflow_tasks(self, tasks, timeout_sec):
        def thread_func(worker, id):
            worker.start()
        tasks = self.__class__.__tasks if tasks is None else tasks
        worker_tasks = WorkerTasks(tasks=self.__class__.__tasks, func=thread_func)
        worker_tasks.run()
        worker_tasks.wait_for_completion(timeout_sec=timeout_sec)
        for task in tasks:
            if task.timeout:
                logs.error('Timeout for %s, node %s', self.__class__.__graph_name, task.id)
                self.__class__.__graph_status.append('failed')
        if 'failed' in self.__class__.__graph_status:
            self.fail('Failure running {}'.format(self.__class__.__graph_name))

    @depends(after=['test_delete_all_active_workflows', 'test_workflows_graphs_delete'])
    def test_node_workflows_post(self):
        # """Testing POST:/nodes/id/workflows"""
        self.post_workflows("Graph.noop-example")
