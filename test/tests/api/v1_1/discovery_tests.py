from config.api1_1_config import *
from config.amqp import *
from modules.logger import Log
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1.rest import ApiException
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis import test
from json import loads
from time import sleep

from tests.api.v1_1.poller_tests import PollerTests
from tests.api.v1_1.workflows_tests import WorkflowsTests
from tests.api.v1_1.obm_settings import obmSettings

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
        workflow = {
            "friendlyName": "set PXE and reboot node",
            "injectableName": "Graph.PXE.Reboot",
            "tasks": [
                {
                    "label": "set-boot-pxe",
                    "taskName": "Task.Obm.Node.PxeBoot",
                },
                {
                    "label": "reboot-start",
                    "taskName": "Task.Obm.Node.Reboot",
                    "waitOn": {
                        "set-boot-pxe": "succeeded"
                    }
                }
            ]
        }

        self.__workflow_instance.put_workflow(workflow)
        self.__workflow_instance.post_workflows("Graph.PXE.Reboot")

    @test(groups=['test_discovery_delete_node'],
            depends_on_groups=["test_discovery_post_reboot", "test-bm-discovery-prepare"])
    def test_node_delete_all(self):
        """ Testing DELETE all compute nodes """
        codes = []
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)

        for n in nodes:
            if n.get('type') == 'compute':
                uuid = n.get('id')
                try:
                    Nodes().nodes_identifier_workflows_active_delete(uuid)
                except ApiException as e:
                    assert_equal(404, e.status, message = 'status should be 404')
                except (TypeError, ValueError) as e:
                    assert(e.message)

                Nodes().nodes_identifier_delete(uuid)
                codes.append(self.__client.last_response)

        assert_not_equal(0, len(codes), message='Delete node list empty!')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)

    @test(groups=['test_discovery_add_obm'],
            depends_on_groups=["test_discovery_delete_node", "test-bm-discovery"])
    def test_node_add_obm(self):
        assert_equal(len(obmSettings().setup_nodes(service_type='ipmi-obm-service')), 0)
