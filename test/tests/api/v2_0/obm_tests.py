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

@test(groups=['obm_api2.tests'])
class OBMTests(object):

    def __init__(self):
        self.__client = config.api_client 

    @test(groups=['obm_api2.tests', 'set-ipmi-obm_api2'], depends_on_groups=['nodes_api2.tests'])
    def setup_ipmi_obm(self):
        """ Setup IPMI OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='ipmi-obm-service')), 0)

    @test(groups=['obm_api2.tests', 'check-obm_api2'], depends_on_groups=['set-ipmi-obm_api2'])
    def check_ipmi_obm_settings(self):
        """ Checking IPMI OBM settings GET:/nodes """
        assert_equal(len(obmSettings().check_nodes(service_type='ipmi-obm-service')), 0, 
                message='there are missing IPMI OBM settings!')
    
    @test(groups=['obm_api2.tests', 'set-snmp-obm_api2'], depends_on_groups=['nodes_api2.tests'])
    def setup_snmp_obm(self):
        """ Setup SNMP OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='snmp-obm-service')), 0)

    @test(groups=['obm_api2.tests', 'check-obm_api2'], depends_on_groups=['set-snmp-obm_api2'])
    def check_snmp_obm_settings(self):
        """ Checking SNMP OBM settings GET:/nodes """
        assert_not_equal(len(obmSettings().check_nodes(service_type='snmp-obm-service')), 0,
                message='there are missing SNMP OBM settings!')
   
    @test(groups=['obm_api2.tests', 'create-node-id-obm-identify_api2'], depends_on_groups=['check-obm_api2'])
    def test_node_id_obm_identify_create(self):
        """ Testing POST:/nodes/:id/obm/identify """
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        codes = []
        data = { "value": "true" }
        for n in nodes:
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Api().nodes_post_obm_id_by_id(identifier=uuid, content=data)
                rsp = self.__client.last_response
                codes.append(rsp)
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Api().nodes_post_obm_id_by_id, 'fooey', data)

    @test(groups=['obm_api2.tests', 'test-obms_api2'])
    def test_obm_library(self):
        """ Testing GET:/obms/library """
        Api().get_obm_lib()
        obms = loads(self.__client.last_response.data)
        services = [t.get('service') for t in obms]
        assert_equal(200, self.__client.last_response.status)
        assert_not_equal(0, len(obms), message='OBM list was empty!')

    @test(groups=['obm_api2.tests', 'test-obms-identifier_api2'])
    def test_obm_library_identifier(self):
        """ Testing GET:/obms/library/:id """
        Api().get_obm_lib()
        obms = loads(self.__client.last_response.data)
        codes = []
        services = [t.get('service') for t in obms]
        for n in services:
            Api().get_obm_lib_by_id(n)
            codes.append(self.__client.last_response)
        assert_not_equal(0, len(obms), message='OBM list was empty!')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)

