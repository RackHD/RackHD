from config.settings import *
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

LOG = Log(__name__)

@test(groups=['obm.tests'])
class OBMTests(object):

    def __init__(self):
        pass
    
    @test(groups=['obm.tests', 'set-ipmi-obm'], depends_on_groups=['nodes.tests'])
    def setup_ipmi_obm(self):
        """ Setup IPMI OBM settings with PATCH:/nodes API """
        assert_equal(len(obmSettings().setup_nodes(service_type='ipmi-obm-service')), 0)

    @test(groups=['obm.tests', 'check-obm'], depends_on_groups=['set-ipmi-obm'])
    def check_ipmi_obm_settings(self):
        """ Checking IPMI OBM settings GET:/nodes API """
        assert_equal(len(obmSettings().check_nodes(service_type='ipmi-obm-service')), 0, 
                message='there are missing IPMI OBM settings!')
    
    @test(groups=['obm.tests', 'set-snmp-obm'], depends_on_groups=['nodes.tests'])
    def setup_snmp_obm(self):
        """ Setup SNMP OBM settings with PATCH:/nodes API """
        assert_equal(len(obmSettings().setup_nodes(service_type='snmp-obm-service')), 0)

    @test(groups=['obm.tests', 'check-obm'], depends_on_groups=['set-snmp-obm'])
    def check_snmp_obm_settings(self):
        """ Checking SNMP OBM settings GET:/nodes API """
        assert_not_equal(len(obmSettings().check_nodes(service_type='snmp-obm-service')), 0,
                message='there are missing SNMP OBM settings!')
   

