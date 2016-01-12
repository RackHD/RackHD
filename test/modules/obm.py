from config.settings import *
from on_http import NodesApi as Nodes
from on_http import rest
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
        Nodes().api1_1_nodes_identifier_catalogs_source_get(uid,'bmc')
        rsp = self.__client.last_response
        bmc = loads(rsp.data)
        if 'data' in bmc:
            mac = bmc['data'].get('MAC Address')
        else:
            Nodes().api1_1_nodes_identifier_catalogs_source_get(uid,'rmm')
            rsp = self.__client.last_response
            rmm = loads(rsp.data)
            if 'data' in rmm:
                mac = bmc['data'].get('MAC Address')
        if mac is not None:
            LOG.debug('BMC MAC {0} for {1}'.format(mac,uid))
            setting = {
                    'service':'ipmi-obm-service',
                    'config': {
                        'user':user,
                        'password':passwd,
                        'host': mac
                    }
            }
            LOG.info('Creating ipmi obm-settings for node {0} \n {1}'.format(uid,setting))
            try:
                Nodes().api1_1_nodes_identifier_patch(uid,setting)
            except rest.ApiException as e:
                LOG.error(e)
                return False
        else:
            LOG.error('Error finding configurable IPMI MAC address for {0}'.format(uid))
            return False

    def setup_nodes(self, service_type, uuid=None):
        err = []
        Nodes().api1_1_nodes_get()
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
                                LOG.info('Successful')
                    if service_type == 'snmp-obm-service' and node_type != 'enclosure':
                        if len(self.check_nodes('snmp-obm-service', uuid=uuid)) > 0:
                            if self._set_snmp(uid) == False:
                                err.append('Error setting SNMP OBM settings for node {0}'.format(uid))
                            else:
                                LOG.info('Successful')
        for e in err:
            LOG.error(e)
        return err

    def check_nodes(self, service_type, uuid=None):
        retval = []
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        for n in nodes:
            node_type = n.get('type')
            uid = n.get('id')
            if uuid is None or uuid == uid:
                if node_type != 'enclosure':
                    obm_obj = n.get('obmSettings')
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


