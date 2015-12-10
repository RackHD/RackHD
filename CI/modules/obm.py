from config.settings import *
from modules.urls import urls
from modules.logger import Log
from modules.nodes import Nodes
from json import dumps

LOG = Log(__name__)

class obmSettings(object):
    def __init__(self, *args, **kwargs):
        self._timerTask = None
        self._nodes = Nodes()

    def _set_snmp(self, uid):
        LOG.warning('_set_snmp() is currently a no-op function')
        return True

    def _set_ipmi(self, uid):
        user, passwd = get_bmc_cred()
        mac = None
        rsp = self._nodes.get_node_catalog(uid,source='bmc')
        bmc = rsp.json()
        if 'data' in bmc:
            mac = bmc['data'].get('MAC Address')
        else:
            rsp = self._nodes.get_node_catalog(uid,source='rmm')
            rmm = rsp.json()
            if 'data' in rmm:
                mac = bmc['data'].get('MAC Address')
        if mac is not None:
            LOG.debug('BMC MAC {0} for {1}'.format(mac,uid))
            setting = dumps({
                'obmSettings':[{
                    'service':'ipmi-obm-service', 
                    'config' : { 
                        'user':user, 
                        'password':passwd,
                        'host': mac 
                    }
                }]
            })
            LOG.info('Creating ipmi obm-settings for node {0}'.format(uid))
            try:
                self._nodes.patch_node(uid,node=setting)
            except Exception as e:
                LOG.error(e.message)
                return False
        else:
            LOG.error('Error finding configurable IPMI MAC address for {0}'.format(uid))
            return False

    def setup_nodes(self, service_type='ipmi-obm-service',uuid=None):
        retval = []
        rsp = self._nodes.get_nodes()
        nodes = rsp.json()
        for n in nodes:
            node_type = n.get('type')
            uid = n.get('id')
            if uuid is None or uuid == uid:
                if service_type == 'ipmi-obm-service' and node_type == 'compute':
                    if self._set_ipmi(uid) == False:
                        retval.append('Error setting IPMI OBM settings for noe {0}'.format(uid))
                if service_type == 'snmp-obm-service' and node_type != 'enclosure':
                    if self._set_snmp(uid) == False:
                        retval.append('Error setting SNMP OBM settings for noe {0}'.format(uid))
        return retval

    def check_nodes(self,service_type='ipmi-obm-service',uuid=None):
        retval = []
        rsp = self._nodes.get_nodes()
        nodes = rsp.json()
        for n in nodes:
            node_type = n.get('type')
            uid = n.get('id')
            if uuid is None or uuid == uid:
                if node_type != 'enclosure':
                    obm_obj = n.get('obmSettings')
                    if obm_obj is None:
                        LOG.error('No OBM settings for node type {0} (id={1})'.format(node_type,uid))
                        retval.append(False)
                    else:
                        for obm in obm_obj:
                            service = obm.get('service')
                            if service_type not in service:
                                LOG.error('No OBM service type {0} (id={1})'.format(service_type,uid))
                                retval.append(False)
        return retval


