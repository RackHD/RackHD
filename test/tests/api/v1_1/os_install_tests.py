from config.api1_1_config import *
from obm_settings import obmSettings
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import rest
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_not_equal
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)

@test(groups=['os-install.v1.1.tests'])
class OSInstallTests(object):

    def __init__(self):
        self.__client = config.api_client 

    @test(groups=['suse-install.v1.1.test'])
    def test_install_suse(self):
        """ Testing SUSE OS Installer Workflow """
        pass
