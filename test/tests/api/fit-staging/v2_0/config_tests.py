from config.api2_0_config import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)


@test(groups=['config_api2.tests'])
class ConfigTests(object):
    def __init__(self):
        self.__client = config.api_client

    @test(groups=['config_api2.tests', 'api2_check-config'])
    def check_server_config(self):
        """Testing GET:api/2.0/config to get server configuration"""
        Api().config_get()
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['api2_patch-config'], depends_on_groups=['api2_check-config'])
    def patch_server_config(self):
        """Testing PATCH:api/2.0/config to patch a specific configuration item"""
        test_pwd = {"PWD": "/this/is/a/test/for/patch_config"}
        LOG.info("Patch PWD with a test path")
        Api().config_patch(config = test_pwd)
        server_config = loads(self.__client.last_response.data)
        assert_equal(server_config.get('PWD'),'/this/is/a/test/for/patch_config', 'Oops patch config failed')
        LOG.info("Doing a check config with test PWD")
        Api().config_get()
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)
        LOG.info("Restoring PWD config after patch test")
        Api().config_patch(config = {"PWD": "/var/renasar/on-http"})
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)

