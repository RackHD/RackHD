from config.settings import *
from on_http import NodesApi as Nodes
from on_http import rest
from modules.obm import obmSettings
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_not_equal
from proboscis import SkipTest
from proboscis import test
from json import loads, dumps

LOG = Log(__name__)

@test(groups=['obm.tests'])
class OBMTests(object):

    def __init__(self):
        self.__client = config.api_client 

    @test(groups=['obm.tests', 'set-ipmi-obm'], depends_on_groups=['nodes.tests'])
    def setup_ipmi_obm(self):
        """ Setup IPMI OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='ipmi-obm-service')), 0)

    @test(groups=['obm.tests', 'check-obm'], depends_on_groups=['set-ipmi-obm'])
    def check_ipmi_obm_settings(self):
        """ Checking IPMI OBM settings GET:/nodes """
        assert_equal(len(obmSettings().check_nodes(service_type='ipmi-obm-service')), 0, 
                message='there are missing IPMI OBM settings!')
    
    @test(groups=['obm.tests', 'set-snmp-obm'], depends_on_groups=['nodes.tests'])
    def setup_snmp_obm(self):
        """ Setup SNMP OBM settings with PATCH:/nodes """
        assert_equal(len(obmSettings().setup_nodes(service_type='snmp-obm-service')), 0)

    @test(groups=['obm.tests', 'check-obm'], depends_on_groups=['set-snmp-obm'])
    def check_snmp_obm_settings(self):
        """ Checking SNMP OBM settings GET:/nodes """
        assert_not_equal(len(obmSettings().check_nodes(service_type='snmp-obm-service')), 0,
                message='there are missing SNMP OBM settings!')
   
    @test(groups=['obm.tests', 'create-node-id-obm-identify'], depends_on_groups=['check-obm'])
    def test_node_id_obm_identify_create(self):
        """ Testing POST:/nodes/:id/obm/identify """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        codes = []
        data = {"value": "true"}
        for n in nodes:
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Nodes().api1_1_nodes_identifier_obm_identify_post(uuid, data)
                rsp = self.__client.last_response
                codes.append(rsp)
        for c in codes:
            assert_equal(200, c.status, message=c.reason)
        assert_raises(rest.ApiException, Nodes().api1_1_nodes_identifier_obm_identify_post, 'fooey', data)

