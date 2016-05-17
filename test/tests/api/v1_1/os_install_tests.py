from config.api1_1_config import *
from config.amqp import *
from modules.logger import Log
from on_http_api1_1 import NodesApi as Nodes
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis import test
from json import loads
from time import sleep

from tests.api.v1_1.poller_tests import PollerTests

LOG = Log(__name__)

@test(groups=['os-install.v1.1.tests'])
class OSInstallTests(object):
    def __init__(self):
        self.__client = config.api_client
        self.__graph_name = None
        self.__task_worker = None

    def __post_workflows(self, graph_name, body):
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)

        for n in nodes:
            if n.get('type') == 'compute':
                id = n.get('id')
                assert_not_equal(id,None)
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

                Nodes().nodes_identifier_workflows_post(id,name=graph_name,body=body)

    @test(groups=['centos7-install.v1.1.test'],
            depends_on_groups=["test-node-poller", "test-bm-bootstrap-prepare"])
    def test_install_centos7(self):
        """ Testing CentOS 7 Installer Workflow """
        body = {
            "options": {
                "defaults": {
                    "version": "7",
                    "rootPassword": "Password0",
                    "hostname": "onrack-ora",
                    "domain": "emc.com",
                    "dnsServers": ["172.12.88.91"]
                }
            }
        }
        self.__post_workflows("Graph.InstallCentOS", body)
