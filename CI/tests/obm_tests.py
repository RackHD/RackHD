from config.settings import *
from modules.obm import obmSettings
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test

LOG = Log(__name__)

@test(groups=['obm.tests'])
class OBMTests(object):

    def __init__(self):
        pass
    
    @test(groups=['obm.tests', 'set-obm'], depends_on_groups=['nodes.tests'])
    def setup_obm(self):
        """ Setup OBM settings with PATCH:/nodes API """
        assert_true(obmSettings().setup_nodes())

    @test(groups=['obm.tests', 'check-obm'], depends_on_groups=['set-obm'])
    def check_ipmi_obm_settings(self):
        """ Checking IPMI OBM settings GET:/nodes API """
        assert_true(obmSettings().check_nodes(service_type='ipmi-obm-service'))
    
    @test(groups=['obm.tests', 'check-obm'], depends_on_groups=['set-obm'])
    def check_snmp_obm_settings(self):
        """ Checking SNMP OBM settings GET:/nodes API """
        assert_true(obmSettings().check_nodes(service_type='ipmi-snmp-service'))
    
