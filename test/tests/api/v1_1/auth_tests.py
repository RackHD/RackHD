from config.api1_1_config import config
from modules.logger import Log
from modules.auth import Auth
from on_http_api1_1 import NodesApi as Nodes
from proboscis.asserts import assert_equal
from proboscis import before_class
from proboscis import after_class
from proboscis import test

LOG = Log(__name__)

@test(groups=['auth.tests'])
class AuthTests(object):

    def __init__(self):
        self.__client = config.api_client

    @before_class()
    def setup(self):
        """setup test environment"""
        Auth.enable()

    @after_class(always_run=True)
    def teardown(self):
        """ restore test environment """
        Auth.disable()

    @test(groups=['test-nodes-withauth'])
    def test_nodes(self):
        """ Testing GET:/nodes """
        Nodes().nodes_get()
        res = self.__client.last_response
        LOG.debug(res.data, json=True)
        assert_equal(200, res.status, message=res.reason)
