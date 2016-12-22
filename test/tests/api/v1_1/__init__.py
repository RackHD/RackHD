# import tests
from nodes_tests import NodesTests
from obm_tests import OBMTests
from amqp_tests import AMQPTests
from lookups_tests import LookupsTests
from profiles_tests import ProfilesTests
from config_tests import ConfigTests
from workflowTasks_tests import WorkflowTasksTests
from workflows_tests import WorkflowsTests
from auth_tests import AuthTests
from os_install_tests import OSInstallTests
from redfish_endpoint_tests import RedfishEndpointTests
from decomission_node_tests import DecommissionNodesTests

tests = [
    'nodes.tests',
    'obm.tests',
    'amqp.tests',
    'lookups.tests',
    'profiles.tests'
    'config.tests',
    'workflowTasks.tests',
    'workflows.tests',
    'redfish-endpoint.v1.1.tests',
    'auth.tests'
]

regression_tests = [
    'os-install.v1.1.tests',
    'deccommission-nodes.v1.1.tests'
]
