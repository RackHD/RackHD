"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import fit_path  # NOQA: unused import
import fit_common
import flogging

from common import api_utils
from nosedep import depends
from config.api2_0_config import config
from obm_settings import obmSettings
from nose.plugins.attrib import attr
logs = flogging.get_loggers()


@attr(regression=False, smoke=True, obm_api2_tests=True)
class OBMTests(fit_common.unittest.TestCase):

    def setUp(self):
        self.__client = config.api_client

    # OBM ipmi-obm-service currently applies to compute nodes
    def test_get_compute_nodes(self):
        nodes = api_utils.api_node_select(self.__client, node_type='compute')
        logs.info(" List of compute nodes: %s", nodes)
        self.assertNotEqual(0, len(nodes), msg='ipmi-obm-service - Node list was empty!')

    # @test(groups=['obm_api2.tests', 'set-ipmi-obm_api2'], depends_on_groups=['nodes_api2.tests'])
    @depends(after='test_get_compute_nodes')
    def test_setup_ipmi_obm_api2(self):
        # """ Setup IPMI OBM settings with PATCH:/nodes """
        self.assertEqual(len(obmSettings().setup_nodes(service_type='ipmi-obm-service')), 0)

    # @test(groups=['obm_api2.tests', 'check-obm_api2'], depends_on_groups=['set-ipmi-obm_api2'])
    @depends(after='test_setup_ipmi_obm_api2')
    def test_check_ipmi_obm_api2_settings(self):
        # """ Checking IPMI OBM settings GET:/nodes """
        self.assertEqual(len(obmSettings().check_nodes(service_type='ipmi-obm-service')), 0,
                         msg='There are missing IPMI OBM settings!')

    # OBM ipmi-snmp-service currently applies to switch and pdu nodes
    def test_get_switch_nodes(self):
        nodes = api_utils.api_node_select(self.__client, node_type='switch')
        logs.info(" List of switch nodes: %s", nodes)
        pdu_nodes = api_utils.api_node_select(self.__client, node_type='pdu')
        logs.info(" List of pdu nodes: %s", pdu_nodes)
        nodes.append(pdu_nodes)
        self.assertNotEqual(0, len(nodes), msg='snmp-obm-service - Node list was empty!')

    # @test(groups=['obm_api2.tests', 'set-snmp-obm_api2'], depends_on_groups=['nodes_api2.tests'])
    @depends(after='test_get_switch_nodes')
    def test_setup_snmp_obm_api2(self):
        # """ Setup SNMP OBM settings with PATCH:/nodes """
        self.assertEqual(len(obmSettings().setup_nodes(service_type='snmp-obm-service')), 0)

    # @test(groups=['obm_api2.tests', 'check-obm_api2'], depends_on_groups=['set-snmp-obm_api2'])
    @depends(after='test_setup_snmp_obm_api2')
    def test_check_snmp_obm_settings(self):
        # """ Checking SNMP OBM settings GET:/nodes """
        self.assertEqual(len(obmSettings().check_nodes(service_type='snmp-obm-service')), 0,
                         msg='There are missing SNMP OBM settings!')
