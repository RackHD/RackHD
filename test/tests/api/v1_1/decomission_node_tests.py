from config.api1_1_config import *
from config.settings import *
from modules.logger import Log
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import LookupsApi
from workflows_tests import WorkflowsTests as workflows
from proboscis.asserts import assert_false
from proboscis.asserts import assert_true
from proboscis import test
from proboscis import after_class
from proboscis import before_class
from json import dumps, loads, load
import pxssh
import os
import time
from obm_settings import obmSettings
import threading


LOG = Log(__name__)
DEFAULT_TIMEOUT = 1600
SSH_USER = 'root'
SSH_PASSWORD = 'RackHDRocks!'
BMC_USER = 'rackhd'

@test(groups=['deccommission-nodes.v1.1.tests'], depends_on_groups=['ubuntu-minimal-install.v1.1.test'])
class DecommissionNodesTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__nodes = []
        Nodes().nodes_get()
        for node in (loads(self.__client.last_response.data)):
            if node['type'] == 'compute':
                self.__nodes.append(node)

    @before_class()
    def setup(self):
        pass

    @after_class(always_run=True)
    def teardown(self):
        return self.__reset_ipmi_obmsettings()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __post_workflow(self, graph_name, nodes, body):
        workflows().post_workflows(graph_name, timeout_sec=DEFAULT_TIMEOUT, nodes=nodes, data=body)

    @test(enabled=True,groups=['ssh.connection.os.installed.test'])
    def validate_os_installed_test(self):
        """ Testing ssh connection to the installed OS"""
        delay = 10
        retries = 5
        assert_true(self.check_ssh_connections(delay, retries),message="couldn't validate OS ssh connetion")

    @test(enabled=True,groups=['set.bmc.credentials.graph.test'], depends_on_groups=['ssh.connection.os.installed.test'])
    def set_bmc_credentials_workflow_test(self):
        """ Testing set BMC credential on compute nodes"""
        self.__set_bmc_credentials(user=BMC_USER)
        LOG.info('Check if bmc user is been added')
        for node in self.__nodes:
            ipmi_resp = self.get_ipmi_user_list(node['id'])
            assert_true(BMC_USER in ipmi_resp,
                    message='failed to create a {0} bmc user for node id {1}'.format(BMC_USER, node['id']))

    @test(enabled=True,groups=['Decommission.graph.test'], depends_on_groups=['set.bmc.credentials.graph.test'])
    def decommission_workflow_test(self):
        """ Testing Decommissioning compute nodes"""
        body = { 'options': {'remove-bmc-credentials': { 'users': ['rackhd']} } }
        self.__post_workflow('Graph.Bootstrap.Decommission.Node', nodes=[], body=body)
            

    @test(enabled=True,groups=['remove.bmc.user.test'], depends_on_groups=['Decommission.graph.test'])
    def remove_bmc_user_test(self):
        """ Testing if decommission workflow removed bmc user from compute nodes"""
        for node in self.__nodes:
            ipmi_resp = self.get_ipmi_user_list(node['id'])
            assert_false(BMC_USER in ipmi_resp,
                    message='failed to delete bmc user {0} for node id {1}'.format(BMC_USER, node['id']))
    
    @test(enabled=True,groups=['erase.disks.test'], depends_on_groups=['Decommission.graph.test'])
    def erase_disks_test(self):
        """ Testing if decommission graph erased the disks on the compute nodes"""
        LOG.info('Finally, check if disks is been deleted')
        is_deleted = self.check_ssh_connections(10, 20)
        assert_false(is_deleted, message='could not clear the disks')

    def check_ssh_connections(self, delay, retries, nodes=[]):
        nodes_list = nodes if len(nodes)!=0 else self.__nodes

        class ShhConnections():
            def __init__(self,host, username, password, nodeid):
                self.host = host
                self.username = username
                self.password = password
                self.node_id = nodeid
                self.is_up = False
                self.thread = None

        def worker(ssh_conn, delay, retries):
            for _ in xrange(retries):
                try:
                    ssh = pxssh.pxssh()
                    ssh.login(ssh_conn.host, ssh_conn.username, ssh_conn.password)
                    ssh_conn.is_up = True
                    LOG.info('set it to True {0}'.format(ssh_conn.is_up))
                    return True 
                except pxssh.ExceptionPxssh  as error:
                    LOG.info('ssh login error {0}'.format(error))
                    #log error
                    time.sleep(delay)
            LOG.warning('could not connet to host {0} node id {1}'.format(ssh_conn.hostname, ssh_conn.node_id))
            return False

        thread_list = []
        for node in nodes_list:
            hosts = self.__lookups_node_ip(node['id'])
            username = SSH_USER
            password = SSH_PASSWORD
            for host in hosts:
                os.popen("ssh-keygen -f ~/.ssh/known_hosts -R {0}".format(host))
                tmp = ShhConnections(host, username, password, node['id'])
                delay = retries = 10
                tmp.thread = threading.Thread(target=worker, args=(tmp,delay, retries))
                thread_list.append(tmp)
        for item in thread_list:
            item.thread.start()
        for item in thread_list:
            item.thread.join(DEFAULT_TIMEOUT)
            if item.is_up != True:
                return False
        return True


    def __lookups_node_ip(self, nodeId):
        LookupsApi().lookups_get(q=nodeId)
        rsp = self.__get_data()
        arr = []
        for entry in rsp:
            if 'ipAddress' in entry:
                arr.append(entry['ipAddress'])
        return arr

    def get_ipmi_user_list(self, nodeId):
        user, passwd = get_bmc_cred()        
        ipmitool_command = "ipmitool -I lanplus -H " + self.__get_bmc_ip(nodeId) + " -U " + user + " -P " + passwd + " user list"
        f = os.popen( ipmitool_command)
        ipmi_response = f.read()
        LOG.info("ipmi user list \n{0}".format(ipmi_response))
        return ipmi_response

    def __get_bmc_ip(self, nodeId):
        Nodes().nodes_identifier_catalogs_source_get(nodeId,'bmc')
        return self.__get_data()['data']['IP Address']

    def __set_bmc_credentials(self, nodes=[], user=None, password=None):
        nodes = nodes if len(nodes) != 0 else self.__nodes
        _workflows = workflows()
        body = {
                'name': 'Graph.Bootstrap.With.BMC.Credentials.Setup',
                'options': {
                    'defaults': {
                        'graphOptions': {
                            'target': '',
                            'generate-pass':{ 'user': user, 'password': password }
                            },
                        'nodeId': ''
                        }
                    }
                }
        for node in nodes:
            body['options']['defaults']['graphOptions']['target'] = \
                    body['options']['defaults']['nodeId'] = \
                    node['id']
            _workflows.post_unbound_workflow('Graph.Bootstrap.With.BMC.Credentials.Setup',data=body,run_now=False)
        _workflows.run_workflow_tasks(None,  DEFAULT_TIMEOUT)
        LOG.info('finiished post bmc set')

    def __reset_ipmi_obmsettings(self):
        obm_setting = obmSettings()
        for node in self.__nodes:
            obmSettings()._set_ipmi(node['id'])
