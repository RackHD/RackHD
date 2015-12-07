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
        return

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
            LOG.info('BMC MAC a{0} for {1}'.format(mac,uid))
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
            rsp = self._nodes.patch_node(uid,node=setting)
            return rsp

    def setup_nodes(self):
        rsp = self._nodes.get_nodes()
        nodes = rsp.json()
        for n in nodes:
            add_ipmi = False
            add_snmp = False
            node_type = n.get('type')
            uid = n.get('id')
            obm_obj = n.get('obmSettings', None)
            if obm_obj is None:
                add_ipmi = True
                add_snmp = True
            else:
                for obm in obm_obj:
                    service = obm.get('service')
                    if "ipmi-obm-service" not in service:
                        add_ipmi = True
                    if "snmp-obm-service" not in service:
                        add_snmp = True
            if add_ipmi and node_type == 'compute':
                self._set_ipmi(uid)
            if add_snmp and node_type != 'enclosure':
                self._set_snmp(uid)
        return True

    def check_nodes(self,service_type='ipmi-obm-service',uuid=None):
        rsp = self._nodes.get_nodes()
        nodes = rsp.json()
        for n in nodes:
            node_type = n.get('type')
            uid = n.get('id')
            if uuid is not None and uuid == uid:
                obm_obj = n.get('obmSettings')
                if node_type != 'enclosure' and obm_obj is None:
                    raise KeyError('Expected obmSettings for node type {0} (id={1})'.format(node_type,uid))
                else:
                    for obm in obm_obj:
                        service = obm.get('service')
                        if service_type not in service:
                            raise ValueError('Expected OBM service type {0} (id={1})'.format(service_type,uid))
        return True


