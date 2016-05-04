from config.api1_1_config import *
from config.amqp import *
from modules.logger import Log
from on_http_api1_1 import NodesApi as Nodes
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis import test
from json import loads
from time import sleep

from tests.api.v1_1.poller_tests import PollerTests
from tests.api.v1_1.workflows_tests import WorkflowsTests

LOG = Log(__name__)

@test(groups=["discovery.tests"])
class DiscoveryTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__graph_name = None
        self.__task_worker = None
        self.__workflow_instance = WorkflowsTests()

    def __get_workflow_status(self, id):
        Nodes().nodes_identifier_workflows_active_get(id)
        status = self.__client.last_response.status
        if status == 200:
            data = loads(self.__client.last_response.data)
            status = data.get('_status')
            assert_is_not_none(status)
        return status

    @test(groups=['test_discovery_post_reboot'], depends_on_groups=["test-node-poller"])
    def test_node_workflows_post_reboot(self):
        """Testing reboot node POST:id/workflows"""
        self.__workflow_instance.post_workflows("Graph.Reboot.Node")

    @test(groups=['test_discovery_reboot_finish'], depends_on_groups=["test_discovery_post_reboot"])
    def test_node_workflows_finish(self):
        """Wait for :id/workflows/active to be updated to empty"""
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)

        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                assert_not_equal(id,None)
                status = self.__get_workflow_status(id)
                timeout = 20
                while status == 'pending' and timeout != 0:
                    LOG.warning('Workflow status for Node {0} (status={1},timeout={2})'.format(id,status,timeout))
                    status = self.__get_workflow_status(id)
                    sleep(5)
                    timeout -= 1
                assert_not_equal(0, timeout, message="Workflow didn't end!")

    @test(groups=['test_discovery_delete_node'],
            depends_on_groups=["test_discovery_reboot_finish", "test-bm-discovery-prepare"])
    def test_node_delete_all(self):
        """ Testing DELETE all compute nodes """
        codes = []
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)

        for n in nodes:
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Nodes().nodes_identifier_delete(uuid)
                codes.append(self.__client.last_response)

        assert_not_equal(0, len(codes), message='Delete node list empty!')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)

