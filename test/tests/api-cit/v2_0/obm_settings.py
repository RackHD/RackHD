"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import fit_path  # NOQA: unused import
import flogging

from config.api2_0_config import config, get_bmc_cred
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from json import loads

logs = flogging.get_loggers()


class obmSettings(object):
    """
    Class to abstract the RackHD Out-of-Band settings
    """

    def __init__(self, *args, **kwargs):
        self.__client = config.api_client

    def _set_snmp(self, uid):
        logs.warning('_set_snmp() is currently a no-op function')
        return True

    def _set_ipmi(self, uid):
        user, passwd = get_bmc_cred()
        mac = None
        Api().nodes_get_catalog_source_by_id(uid, 'bmc')
        rsp = self.__client.last_response
        bmc = loads(rsp.data)
        if 'data' in bmc:
            mac = bmc['data'].get('MAC Address')
        else:
            Api().nodes_get_catalog_source_by_id(uid, 'rmm')
            rsp = self.__client.last_response
            rmm = loads(rsp.data)
            if 'data' in rmm:
                mac = bmc['data'].get('MAC Address')
        if mac is not None:
            logs.debug('BMC MAC %s for %s', mac, uid)
            logs.debug('BMC user %s passowd %s', user, passwd)
            setting = {
                'nodeId': uid,
                'service': 'ipmi-obm-service',
                'config': {
                    'user': user,
                    'password': passwd,
                    'host': mac
                }
            }
            logs.info('Creating ipmi obm-settings for node %s : %s', uid, setting)
            try:
                Api().obms_put(setting)
                rsp = self.__client.last_response
                logs.debug(" IPMI OBM Set response %s", str(rsp.status))
            except ApiException as e:
                logs.error(e)
                return False
        else:
            logs.error('Error finding configurable IPMI MAC address for %s', uid)
            return False
        return True

    def setup_nodes(self, service_type, uuid=None):
        err = []
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            node_type = n.get('type')
            uid = n.get('id')
            if uuid is None or uuid == uid:
                    if service_type == 'ipmi-obm-service' and node_type == 'compute':
                        if len(self.check_nodes('ipmi-obm-service', uuid=uuid)) > 0:
                            if not self._set_ipmi(uid):
                                err.append('Error setting IPMI OBM settings for node {0}'.format(uid))
                            else:
                                logs.info('Setting IPMI OBM settings successful')
                    if service_type == 'snmp-obm-service' and node_type != 'enclosure' and node_type != 'compute':
                        if len(self.check_nodes('snmp-obm-service', uuid=uuid)) > 0:
                            if not self._set_snmp(uid):
                                err.append('Error setting SNMP OBM settings for node {0}'.format(uid))
                            else:
                                logs.info('Setting SNMP OBM settings successful')
        for e in err:
            logs.error(e)
        return err

    def check_nodes(self, service_type, uuid=None):
        retval = []
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            node_type = n.get('type')
            uid = n.get('id')
            if uuid is None or uuid == uid:
                if node_type != 'enclosure':
                    logs.info("Checking node: %s type %s", uid, node_type)
                    obm_obj = []
                    Api().obms_get()
                    all_obms = loads(self.__client.last_response.data)
                    for obm in all_obms:
                        node_ref = obm.get('node')
                        if node_ref == uid or node_ref.split('/')[-1] == uid:
                            obm_obj.append(obm)
                    if (obm_obj is None) or (obm_obj is not None and len(obm_obj) == 0):
                        # need to check if the failure is real depending on the node type
                        if service_type == 'snmp-obm-service' and node_type in ['switch', 'pdu']:
                            logs.warning('snmp-obm-service - No OBM settings for node type %s (id=%s)', node_type, uid)
                            retval.append(False)
                        elif service_type == 'ipmi-obm-service' and node_type == 'compute':
                            logs.warning('ipmi-obm-service - No OBM settings for node type %s (id=%s)', node_type, uid)
                            retval.append(False)
                    else:
                        for obm in obm_obj:
                            service = obm.get('service')
                            if service_type not in service:
                                if service_type == 'snmp-obm-service' and node_type in ['switch', 'pdu']:
                                    logs.warning('No OBM service type %s (id=%s, type=%s)', service_type, uid, node_type)
                                    retval.append(False)
                                elif service_type == 'ipmi-obm-service' and node_type in ['compute']:
                                    logs.warning('No OBM service type %s (id=%s, type=%s)', service_type, uid, node_type)
                                    retval.append(False)
        return retval
