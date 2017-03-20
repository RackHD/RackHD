from config.api2_0_config import *
from obm_settings import obmSettings
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
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

@test(groups=['obm_api2.tests'], depends_on_groups=['nodes.api2.discovery.test'])
class OBMTests(object):

    def __init__(self):
        self.__client = config.api_client 

    @test(groups=['obm_api2.tests', 'set-ipmi-obm_api2'])
    def setup_ipmi_obm(self):
        """ Setup IPMI OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='ipmi-obm-service')), 0)

    @test(groups=['obm_api2.tests', 'check-obm_api2'], depends_on_groups=['set-ipmi-obm_api2'])
    def check_ipmi_obm_settings(self):
        """ Checking IPMI OBM settings GET:/nodes """
        assert_equal(len(obmSettings().check_nodes(service_type='ipmi-obm-service')), 0, 
                message='there are missing IPMI OBM settings!')
    
    @test(groups=['obm_api2.tests', 'set-snmp-obm_api2'])
    def setup_snmp_obm(self):
        """ Setup SNMP OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='snmp-obm-service')), 0)

    @test(groups=['obm_api2.tests', 'check-obm_api2'], depends_on_groups=['set-snmp-obm_api2'])
    def check_snmp_obm_settings(self):
        """ Checking SNMP OBM settings GET:/nodes """
        assert_not_equal(len(obmSettings().check_nodes(service_type='snmp-obm-service')), 0,
                message='there are missing SNMP OBM settings!')
