"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from json import loads
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['config_api2.tests'])
@attr(regression=False, smoke=True, config_api2_tests=True)
class ConfigTests(fit_common.unittest.TestCase):
    def setUp(self):
        self.__client = config.api_client

    # @test(groups=['config_api2.tests', 'api2_check-config'])
    def test_check_server_config(self):
        # """Testing GET:api/2.0/config to get server configuration"""
        Api().config_get()
        rsp = self.__client.last_response
        self.assertEqual(200, rsp.status, msg=rsp.reason)

    # @test(groups=['api2_patch-config'], depends_on_groups=['api2_check-config'])
    @depends(after=test_check_server_config)
    def test_patch_server_config(self):
        # """Testing PATCH:api/2.0/config to patch a specific configuration item"""
        test_pwd = {"PWD": "/this/is/a/test/for/patch_config"}
        logs.info(" Patch PWD with a test path")
        Api().config_patch(config=test_pwd)
        server_config = loads(self.__client.last_response.data)
        self.assertEqual(server_config.get('PWD'), '/this/is/a/test/for/patch_config',
                         msg='Oops patch config failed')
        logs.info(" Doing a check config with test PWD")
        Api().config_get()
        rsp = self.__client.last_response
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        logs.info(" Restoring PWD config after patch test")
        Api().config_patch(config={"PWD": "/var/renasar/on-http"})
        rsp = self.__client.last_response
        self.assertEqual(200, rsp.status, msg=rsp.reason)
