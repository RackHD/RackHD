'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from json import loads, dumps
from nose.plugins.attrib import attr
from nosedep import depends
from sm_plugin import smp_get_stream_monitor

logs = flogging.get_loggers()

HTTP_NO_CONTENT = 204
HTTP_NOT_FOUND = 404


@attr(regression=False, smoke=True, workflows_api2_tests=True)
class WorkflowsTests(fit_common.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        # Get the stream-monitor plugin for AMQP
        cls._amqp_sp = smp_get_stream_monitor('amqp')

        if cls._amqp_sp and cls._amqp_sp.has_amqp_server:
            # Create the "all events" tracker
            cls._on_events_tracker = cls._amqp_sp.create_tracker('wf-on-events-all', 'on.events', '#')
        else:
            cls._on_events_tracker = None

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

    def setUp(self):
        if not self._on_events_tracker:
            raise fit_common.unittest.SkipTest('Skipping AMQP test because no AMQP server defined')

        # attach a processor to the on-events-tracker amqp tracker. Then we can
        # attach indiviual match-clauses to this in each test-case.
        self.__qproc = self._amqp_sp.get_tracker_queue_processor(self._on_events_tracker, start_at='now')

    def __get_result(self):
        return self.__client.last_response

    def __get_data(self):
        return loads(self.__get_result().data)

    def test_delete_all_active_workflows(self):
        # """Testing node PUT:/nodes/identifier/workflows/action"""
        Api().nodes_get_all()
        nodes = self.__get_data()
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
        self.assertEqual(200, self.__get_result().status)
        self.assertNotEqual(0, len(self.__get_data()),
                            msg='Active workflows list was empty!')

    @depends(after='test_workflows_get')
    def test_workflows_post(self):
        # """Testing POST:/workflows"""
        Api().workflows_post(body={"name": 'Graph.noop-example'})
        self.assertEqual(201, self.__get_result().status)
        rawj = loads(self.__get_result().data)
        instance_id = rawj.get('instanceId')
        self.assertIsNotNone(instance_id)
        self.assertEqual('Graph.noop-example', str(rawj['definition'].get('injectableName')))

    @depends(after='test_workflows_get')
    def test_workflows_id_get(self):
        # """ Testing GET:/workflows/identifier"""

        # Getting the identifier of the first workflow in order to validate the get-id function
        Api().workflows_get()
        rawj = self.__get_data()
        instance_id = rawj[0].get('instanceId')
        self.assertIsNotNone(instance_id)
        Api().workflows_get_by_instance_id(instance_id)
        self.assertEqual(200, self.__get_result().status)

    @depends(after='test_workflows_get')
    def test_negative_workflows_id_get(self):
        # """ Negative Testing GET:/workflows/identifier"""
        try:
            Api().workflows_get_by_instance_id("WrongIdentifier")
            self.assertEqual(404, self.__get_result(), msg='status should be 404. No exception raised')
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))
        except (TypeError, ValueError) as e:
            assert(e.message)

    def test_workflows_graphs_get(self):
        # """Testing GET:/workflows/graphs"""
        Api().workflows_get_graphs()
        self.assertEqual(200, self.__get_result().status)
        resp = self.__get_data()
        logs.debug_6(" Workflow graphs: %s", dumps(resp, indent=4))
        self.assertNotEqual(0, len(self.__get_data()),
                            msg='Workflows list was empty!')

    def test_workflows_graphs_put(self):
        # """ Testing PUT:/workflows/graphs """

        # Make sure there is no workflowTask with the same name
        Api().workflows_get_graphs_by_name('*')
        rawj = self.__get_data()

        for i, var in enumerate(rawj):
            if self.workflowDict['injectableName'] == str(rawj[i].get('injectableName')):
                fnameList = str(rawj[i].get('friendlyName')).split('_')
                suffix = int(fnameList[1]) + 1
                self.workflowDict['friendlyName'] = fnameList[0] + '_' + str(suffix)
                break

        # Add a workflow task
        logs.info("Adding workflow task: %s ", str(self.workflowDict))
        Api().workflows_put_graphs(body=self.workflowDict)
        self.assertEqual(201, self.__get_result().status)

        # Validate the content
        Api().workflows_get_graphs()
        rawj = self.__get_data()
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
        self.assertEqual(200, self.__get_result().status)
        rawj = self.__get_data()
        self.assertEqual(self.workflowDict.get('friendlyName'), str(rawj[0].get('friendlyName')))

    @depends(after='test_workflows_library_id_get')
    def test_workflows_graphs_name_put(self):
        # """Testing PUT:/workflows/graphs"""
        # Test updating a graph
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = self.__get_data()
        self.assertEqual(self.workflowDict.get('friendlyName'), str(rawj[0].get('friendlyName')))
        Api().workflows_put_graphs(body=self.workflowDict2)
        self.assertEqual(201, self.__get_result().status)
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = self.__get_data()
        self.assertEqual(self.workflowDict2.get('friendlyName'), str(rawj[0].get('friendlyName')))

    @depends(after='test_workflows_graphs_name_put')
    def test_workflows_graphs_delete(self):
        # """Testing DELETE:/workflows/graphs/injectableName"""
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        rawj = self.__get_data()
        self.assertEqual(self.workflowDict2.get('friendlyName'), str(rawj[0].get('friendlyName')))
        Api().workflows_delete_graphs_by_name(self.workflowDict.get('injectableName'))
        self.assertEqual(204, self.__get_result().status)
        Api().workflows_get_graphs_by_name(self.workflowDict.get('injectableName'))
        self.assertEqual(0, len(self.__get_data()))

    @depends(after=['test_workflows_graphs_name_put', 'test_delete_all_active_workflows'])
    def test_node_workflows_post(self):
        # """Testing POST:/nodes/id/workflows"""
        self.post_workflows("Graph.noop-example")

    def post_workflows(self, graph_name, timeout_sec=10, nodes=[], data=None,
                       tasks=None, callback=None, run_now=True):
        self.__class__.__graph_name = graph_name
        self.__class__.__graph_status = []

        # clean up the defaults
        tasks = tasks if tasks else []
        data = data if data else {}

        if len(nodes) == 0:
            Api().nodes_get_all()
            nodes = self.__get_data()

        for n in nodes:
            if n.get('type') == 'compute' and n.get('sku'):
                logs.debug("node is compute")
                node_id = n.get('id')
                self.assertIsNotNone(node_id)
                logs.debug(' Starting amqp listener for node %s', node_id)

                # make sure to cannel any possible active workflow
                self.__cancel_active_workflow(node_id)

                # post new workflow
                Api().nodes_post_workflow_by_id(node_id, name=self.__class__.__graph_name, body=data)
                logs.info("Posted workflow %s on node %s", self.__class__.__graph_name, node_id)
                rsp_data = self.__get_data()
                workflow_id = rsp_data['instanceId']
                logs.info("*************** Posted workflow id %s on node %s", workflow_id, node_id)

                self.__qproc.match_on_routekey('post-graph-finish',
                                               routing_key='graph.finished.{}'.format(workflow_id),
                                               validation_block=self.__build_workflow_node_post_block(workflow_id))

                self.__qproc.match_on_routekey('post-graph-finish-infomation',
                                               routing_key='graph.finished.information.{}.{}'.format(workflow_id, node_id))

        results = self._amqp_sp.finish(timeout=360)
        results[0].assert_errors(self)

    def __cancel_active_workflow(self, node_id):
        # Cancel any possible running workflows
        try:
            Api().nodes_workflow_action_by_id(node_id, {'command': 'cancel'})
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))
        except (TypeError, ValueError) as e:
            assert(e.message)

    def __build_workflow_node_post_block(self, workflow_id):
        expected_payload = {
            "status": 'succeeded'
        }

        expected_rk = "graph.finished.{}".format(workflow_id)

        ex = {
            'body': expected_payload,
            'routing_key': expected_rk
        }
        return ex
