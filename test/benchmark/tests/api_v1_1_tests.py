import time

from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_false
from proboscis import SkipTest
from proboscis import test
from proboscis import before_class
from proboscis import after_class
from json import loads

from modules.logger import Log
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
from config.api1_1_config import *
from config.amqp import *
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import WorkflowApi as Workflows
from tests.api.v1_1.discovery_tests import DiscoveryTests
from tests.api.v1_1.poller_tests import PollerTests
from tests.api.v1_1.workflows_tests import WorkflowsTests

from benchmark.tests import ansible_ctl
from benchmark.utils import parser
from benchmark.utils.case_recorder import caseRecorder

LOG = Log(__name__)

class BenchmarkTests(object):
    def __init__(self, name):
        ansible_ctl.render_case_name(name)
        self.__data_path = ansible_ctl.get_data_path_per_case()
        self.case_recorder = caseRecorder(self.__data_path)
        self.client = config.api_client
        self.__node_count = 0
        self.__finished = 0
        self.__graph_name = None

    def _prepare_case_env(self):
        self.__node_count = self.__check_compute_count()
        self.case_recorder.write_interval(ansible_ctl.get_data_interval())
        self.case_recorder.write_start()
        self.case_recorder.write_node_number(self.__node_count)

        assert_equal(True, ansible_ctl.start_daemon(), \
                    message='Failed to start data collection daemon!')

    def _collect_case_data(self):
        assert_equal(True, ansible_ctl.collect_data(), message='Failed to collect footprint data!')
        self.case_recorder.write_end()

        LOG.info('Parse log and generate html reports')
        try:
            parser.parse(self.__data_path)
        except RuntimeError as err:
            LOG.warning('Error on parsing log or generating reports: ')
            LOG.warning(err)

    def _wait_until_graph_finish(self, graph_name, timevalue):
        self.__graph_name = graph_name
        self.__task = WorkerThread(AMQPWorker(queue=QUEUE_GRAPH_FINISH, \
                                              callbacks=[self.__handle_graph_finish]), \
                                   graph_name)
        def start(worker, id):
            worker.start()
        tasks = WorkerTasks(tasks=[self.__task], func=start)
        tasks.run()
        tasks.wait_for_completion(timeout_sec=timevalue)
        assert_false(self.__task.timeout, \
            message='timeout waiting for task {0}'.format(self.__task.id))

    def __handle_graph_finish(self, body, message):
        routeId = message.delivery_info.get('routing_key').split('graph.finished.')[1]
        Workflows().workflows_get()
        workflows = loads(self.client.last_response.data)

        message.ack()
        for w in workflows:
            definition = w['definition']
            injectableName = definition.get('injectableName')
            if injectableName == self.__graph_name:
                graphId = w['context'].get('graphId')
                if graphId == routeId:
                    nodeid = w['context'].get('target')
                    if nodeid == None:
                        nodeid = w['definition']['options']['defaults'].get('nodeId','')
                    status = body.get('status')
                    if status == 'succeeded':
                        self.__finished += 1
                        self.case_recorder.write_event('finish {0} on node {1} {2}'
                                .format(self.__graph_name, self.__finished, nodeid))
                        break

        if self.__node_count == self.__finished:
            self.__task.worker.stop()
            self.__task.running = False
            self.__finished = 0
            self._collect_case_data()
            LOG.info('Fetch {0} log finished'.format(self.__graph_name))

    def __check_compute_count(self):
        Nodes().nodes_get()
        nodes = loads(self.client.last_response.data)
        count = 0
        for n in nodes:
            type = n.get('type')
            if type == 'compute':
                count += 1
        return count

@test(groups=["benchmark.poller"])
class BenchmarkPollerTests(BenchmarkTests):
    def __init__(self):
        BenchmarkTests.__init__(self, 'poller')

    @test(groups=["test-bm-poller"], depends_on_groups=["test-node-poller"])
    def test_poller(self):
        """ Wait for 15 mins to let RackHD run pollers """
        self._prepare_case_env()
        time.sleep(900)
        self._collect_case_data()
        LOG.info('Fetch poller log finished')

@test(groups=["benchmark.discovery"])
class BenchmarkDiscoveryTests(BenchmarkTests):
    def __init__(self):
        BenchmarkTests.__init__(self, 'discovery')

    @test(groups=["test-bm-discovery-prepare"], depends_on_groups=["test-node-poller"])
    def test_prepare_discovery(self):
        """ Prepare discovery """
        self._prepare_case_env()

    @test(groups=["test-bm-discovery"],
            depends_on_groups=["test-bm-discovery-prepare", "test_discovery_delete_node"])
    def test_discovery(self):
        """ Wait for discovery finished """
        self.case_recorder.write_event('start all discovery')
        self._wait_until_graph_finish('Graph.SKU.Discovery', 1200)

    @test(groups=["test-bm-discovery-post"],
            depends_on_groups=["test_discovery_add_obm"])
    def test_discovery_post(self):
        pass

@test(groups=["benchmark.bootstrap"])
class BenchmarkBootstrapTests(BenchmarkTests):
    def __init__(self):
        BenchmarkTests.__init__(self, 'bootstrap')
        self.__base = defaults.get('RACKHD_BASE_REPO_URL', \
            'http://{0}:{1}'.format(HOST_IP, HOST_PORT))
        self.__os_repo = defaults.get('RACKHD_CENTOS_REPO_PATH', \
            self.__base + '/repo/centos/7')
    @test(groups=["test-bm-bootstrap-prepare"], depends_on_groups=["test-node-poller"])
    def test_prepare_bootstrap(self):
        """ Prepare bootstrap """
        self._prepare_case_env()

    @test(groups=['test-bm-bootstrap-post-centos7'],
            depends_on_groups=["test-bm-bootstrap-prepare"])
    def test_install_centos7(self):
        """ Testing CentOS 7 Installer Workflow """

        self.case_recorder.write_event('start all bootstrap')
        body = {
            "options": {
                "defaults": {
                    "version": "7",
                    "repo": self.__os_repo
                }
            }
        }

        WorkflowsTests().post_workflows("Graph.InstallCentOS",
                                        nodes=[],
                                        data=body,
                                        run_now=False)

    @test(groups=["test-bm-bootstrap"],
            depends_on_groups=["test-bm-bootstrap-prepare", "test-bm-bootstrap-post-centos7"])
    def test_bootstrap_centos(self):
        """ Wait for bootstrap finished """
        self.case_recorder.write_event('start all bootstrap')
        self._wait_until_graph_finish('Graph.InstallCentOS', -1)
