from config.api1_1_config import *
from modules.logger import Log
from on_http import ConfigApi as Config
from on_http import NodesApi as Nodes
from on_http import rest
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)


@test(groups=['config.tests'])
class ConfigTests(object):
    def __init__(self):
        self.__client = config.api_client

    @test(groups=['config.tests', 'check-config'])
    def check_server_config(self):
        """Testing GET:/config to get server configuration"""
        Config().api1_1_config_get()
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['patch-config'], depends_on_groups=['check-config'])
    def patch_server_config(self):
        """Testing PATCH:/config to patch a specific configuration item"""
        test_pwd = {"PWD": "/this/is/a/test/for/patch_config"}
        LOG.info("Patch PWD with a test path")
        Config().api1_1_config_patch(body=test_pwd)
        server_config = loads(self.__client.last_response.data)
        assert_equal(server_config.get('PWD'),'/this/is/a/test/for/patch_config', 'Oops patch config failed')
        LOG.info("Doing a check config with test PWD")
        Config().api1_1_config_get()
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)
        LOG.info("Restoring PWD config after patch test")
        Config().api1_1_config_patch(body = {"PWD": "/var/renasar/on-http"})
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)

