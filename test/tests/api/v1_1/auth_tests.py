from config.api1_1_config import *
from modules.logger import Log
from modules.auth import Auth
from on_http import NodesApi as Nodes
from proboscis.asserts import assert_equal
from proboscis import before_class
from proboscis import after_class
from proboscis import test

LOG = Log(__name__)

@test(groups=['auth.tests'])
class AuthTests(object):

    def __init__(self):
        self.__auth = Auth()

    @before_class()
    def setup(self):
        """setup test environment"""
        self.__auth.enable()

    @after_class(always_run=True)
    def teardown(self):
        """ restore test environment """
        self.__auth.disable()

    @test(groups=['test-nodes-withauth'])
    def test_nodes(self):
        """ Testing GET:/nodes """
        Nodes().api1_1_nodes_get()
        res = config.api_client.last_response
        LOG.debug(res.data, json=True)
        assert_equal(200, res.status, message=res.reason)
