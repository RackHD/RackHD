from config.api2_0_config import *
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from modules.logger import Log
from json import dumps, loads

LOG = Log(__name__)

"""
Class to abstract the RackHD Out-of-Band settings 
"""
class obmSettings(object):
    def __init__(self, *args, **kwargs):
        self.__client = config.api_client

    def _set_snmp(self, uid):
        LOG.warning('_set_snmp() is currently a no-op function')
        return True

    def _set_ipmi(self, uid):
        user, passwd = get_bmc_cred()
        mac = None
        Api().nodes_get_catalog_source_by_id(uid,'bmc')
        rsp = self.__client.last_response
        bmc = loads(rsp.data)
        if 'data' in bmc:
            mac = bmc['data'].get('MAC Address')
        else:
            Api().nodes_get_catalog_source_by_id(uid,'rmm')
            rsp = self.__client.last_response
            rmm = loads(rsp.data)
            if 'data' in rmm:
                mac = bmc['data'].get('MAC Address')
        if mac is not None:
            LOG.debug('BMC MAC {0} for {1}'.format(mac,uid))
            setting = {
                'nodeId': uid,
                'service':'ipmi-obm-service',
                'config': {
                    'user':user,
                    'password':passwd,
                    'host': mac
                }
            }
            LOG.info('Creating ipmi obm-settings for node {0} \n {1}'.format(uid,setting))
            try:
                Api().obms_put(setting)
            except rest.ApiException as e:
                LOG.error(e)
                return False
        else:
            LOG.error('Error finding configurable IPMI MAC address for {0}'.format(uid))
            return False

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
                            if self._set_ipmi(uid) == False:
                                err.append('Error setting IPMI OBM settings for node {0}'.format(uid))
                            else:
                                LOG.info('Setting IPMI OBM settings successful')
                    if service_type == 'snmp-obm-service' and node_type != 'enclosure':
                        if len(self.check_nodes('snmp-obm-service', uuid=uuid)) > 0:
                            if self._set_snmp(uid) == False:
                                err.append('Error setting SNMP OBM settings for node {0}'.format(uid))
                            else:
                                LOG.info('Setting SNMP OBM settings successful')
        for e in err:
            LOG.error(e)
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
                    obm_obj = []
                    Api().obms_get()
                    all_obms = loads(self.__client.last_response.data)
                    for obm in all_obms:
                        node_ref = obm.get('node')
                        if node_ref == uid or node_ref.split('/')[-1] == uid:
                            obm_obj.append(obm)
                    if (obm_obj is None) or (obm_obj is not None and len(obm_obj)== 0):
                        LOG.warning('No OBM settings for node type {0} (id={1})'.format(node_type,uid))
                        retval.append(False)
                    else:
                        for obm in obm_obj:
                            service = obm.get('service')
                            if service_type not in service:
                                LOG.warning('No OBM service type {0} (id={1})'.format(service_type,uid))
                                retval.append(False)
        return retval


