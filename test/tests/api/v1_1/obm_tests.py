from config.api1_1_config import *
from obm_settings import obmSettings
from on_http_api1_1 import ObmsApi as Obms
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

@test(groups=['obm.tests'])
class OBMTests(object):

    def __init__(self):
        self.__client = config.api_client 

    @test(groups=['set-ipmi-obm'], 
        depends_on_groups=['check-nodes-catalogs.test'])
    def setup_ipmi_obm(self):
        """ Setup IPMI OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='ipmi-obm-service')), 0)

    @test(groups=['check-ipmi-obm'], depends_on_groups=['set-ipmi-obm'])
    def check_ipmi_obm_settings(self):
        """ Checking IPMI OBM settings GET:/nodes """
        assert_equal(len(obmSettings().check_nodes(service_type='ipmi-obm-service')), 0, 
                message='there are missing IPMI OBM settings!')
    
    @test(groups=['set-snmp-obm'], \
        depends_on_groups=['check-nodes-catalogs.test'])
    def setup_snmp_obm(self):
        """ Setup SNMP OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='snmp-obm-service')), 0)

    @test(groups=['check-snmp-obm'], depends_on_groups=['set-snmp-obm'])
    def check_snmp_obm_settings(self):
        """ Checking SNMP OBM settings GET:/nodes """
        assert_not_equal(len(obmSettings().check_nodes(service_type='snmp-obm-service')), 0,
                message='there are missing SNMP OBM settings!')
   
    @test(groups=['create-node-id-obm-identify'], \
        depends_on_groups=['check-ipmi-obm', 'check-snmp-obm'])
    def test_node_id_obm_identify_create(self):
        """ Testing POST:/nodes/:id/obm/identify """
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        codes = []
        data = {"value": "true"}
        for n in nodes:
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Nodes().nodes_identifier_obm_identify_post(uuid, data)
                rsp = self.__client.last_response
                codes.append(rsp)
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().nodes_identifier_obm_identify_post, 'fooey', data)

    @test(groups=['test-obm-library.tests'])
    def test_obm_library(self):
        """ Testing GET:/obms/library """
        Obms().obms_library_get()
        obms = loads(self.__client.last_response.data)
        services = [t.get('service') for t in obms]
        assert_equal(200, self.__client.last_response.status)
        assert_not_equal(0, len(obms), message='OBM list was empty!')

    @test(groups=['test-obms-identifier.tests'])
    def test_obm_library_identifier(self):
        """ Testing GET:/obms/library/:id """
        Obms().obms_library_get()
        obms = loads(self.__client.last_response.data)
        codes = []
        services = [t.get('service') for t in obms]
        for n in services:
            Obms().obms_library_identifier_get(n)
            codes.append(self.__client.last_response)
        assert_not_equal(0, len(obms), message='OBM list was empty!')
        for c in codes:
            assert_equal(200, c.status, message=c.reason)

