from config.api2_0_config import *
from config.settings import *
from modules.logger import Log
from workflows_tests import WorkflowsTests as workflows
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_true
from proboscis import test
from proboscis import after_class
from proboscis import before_class
from json import loads
from on_http_api2_0 import ApiApi as Api
from obm_settings import obmSettings
import os
import datetime as date
import time
from on_http_api2_0.rest import ApiException
import pxssh
import threading


LOG = Log(__name__)
SSH_USER = 'root'
SSH_PASSWORD = 'RackHDRocks!'
# default user
BMC_USER = 'rackhd'
# Select one node to run OS install
NODE_INDEX = defaults.get('NODE_INDEX', None)
DEFAULT_TIMEOUT_SEC = 1020
SSH_CONNECTION_TIMEOUT = 600


@test(groups=['deccommission-nodes.v2.0.tests'], depends_on_groups=['centos-6-5-minimal-install.v2.0.test'])
class DecommissionNodesTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__nodes = []
        Api().nodes_get_all()
        for node in (loads(self.__client.last_response.data)):
            if node['type'] == 'compute':
                self.__nodes.append(node)
        self.__nodes = sorted(self.__nodes, key=lambda k: k['id'])

    @before_class()
    def setup(self):
        pass

    @after_class(always_run=True)
    def teardown(self):
        return self.__reset_ipmi_obmsettings()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __get_used_nodes(self):
        index = None
        nodes = []
        try:
            index = int(NODE_INDEX)
            nodes = [self.__nodes[index]]
        except:
            nodes = self.__nodes
        return nodes

    def __wait_for_completion(self, node, graph_name, graph_instance):
        id = node.get('id')
        start_time = date.datetime.now()
        current_time = date.datetime.now()
        # Collect BMC info
        Api().nodes_get_catalog_source_by_id(identifier=id, source='bmc')
        bmc_data = self.__get_data().get('data')
        bmc_ip = bmc_data.get('IP Address')
        LOG.info('running test on node : {0} with BMC IP: {1}'.format(id, bmc_ip))
        while True:
            if (current_time - start_time).total_seconds() > DEFAULT_TIMEOUT_SEC:
                raise Exception('Timed out after {0} seconds'.format(DEFAULT_TIMEOUT_SEC))
                break
            Api().workflows_get()
            workflows = self.__get_data()
            for w in workflows:
                # LOG.info('print w : {0} {1} {2}'.format(w.get('injectableName'), w.get('node'), w.get('instanceId')))
                if (w.get('injectableName') == graph_name and
                        w.get('instanceId') == graph_instance):
                    status = w.get('status')
                    # LOG.info('{0} - target: {1}, status: {2}'.format(w.get('injectableName'), w.get('node'), status))
                    if status == 'succeeded' or status == 'failed' or status == 'canceled':
                        msg = {
                            'graph_name': w.get('injectableName'),
                            'target': id,
                            'status': status,
                            'graph_instance': graph_instance
                        }
                        if status == 'failed' or status == 'canceled':
                            msg['active_task'] = w['tasks']
                            LOG.error(msg, json=True)
                        else:
                            LOG.info(msg, json=True)
                        assert_equal(status, 'succeeded', message='test failed')
                        return
            time.sleep(10)
            current_time = date.datetime.now()
            # LOG.info('current time {0} vs start time {1}'.format(current_time, start_time))

    def __post_workflow(self, graph_name, nodes, body=None):
        # check if NODE_INDEX is set
        index = None
        try:
            index = int(NODE_INDEX)
        except:
            LOG.info('NODE_INDEX env is not set')
            workflows().post_workflows(graph_name, timeout_sec=DEFAULT_TIMEOUT_SEC, nodes=nodes, data=body)
            return

        # check if index is in the array range
        if index >= len(self.__nodes):
            raise Exception('index is outside the array range index: {0} vs nodes len {1}'.format(index, len(nodes)))
            return
        LOG.info('node index is set to {0}'.format(index))
        node = self.__nodes[index]
        id = node.get('id')
        # delete active workflow on the selected node
        try:
            Api().nodes_workflow_action_by_id(id, {'command': 'cancel'})
        except ApiException as e:
            assert_equal(404, e.status, message='status should be 404')
        Api().nodes_post_workflow_by_id(id, name=graph_name, body=body)
        log_context = self.__get_data().get('logContext')
        if log_context is None:
            raise Exception('Could not find logContext in {0}'.format(self.__get_data()))
            return
        # load graph instance id
        graph_instance = log_context.get('graphInstance')
        return self.__wait_for_completion(node, graph_name, graph_instance)

    def __lookups_node_ip(self, nodeId):
        Api().lookups_get(q=nodeId)
        rsp = self.__get_data()
        arr = []
        for entry in rsp:
            if 'ipAddress' in entry:
                arr.append(entry['ipAddress'])
        return arr

    def get_ipmi_user_list(self, nodeId):
        user, passwd = get_bmc_cred()
        ipmitool_command = "ipmitool -I lanplus -H " + \
                           self.__get_bmc_ip(nodeId) + " -U " + user + " -P " + passwd + " user list"
        f = os.popen(ipmitool_command)
        ipmi_response = f.read()
        LOG.info("ipmi user list \n{0}".format(ipmi_response))
        return ipmi_response

    def __get_bmc_ip(self, nodeId):
        Api().nodes_get_catalog_source_by_id(identifier=nodeId, source='bmc')
        return self.__get_data()['data']['IP Address']

    def __reset_ipmi_obmsettings(self):
        for node in self.__get_used_nodes():
            obmSettings()._set_ipmi(node['id'])

    def __set_bmc_credentials(self, nodes=[], user=None, password=None):
        nodes = nodes if len(nodes) != 0 else self.__nodes
        _workflows = workflows()
        body = {
            'name': 'Graph.Bootstrap.With.BMC.Credentials.Setup',
            'options': {
                'defaults': {
                    'graphOptions': {
                        'target': '',
                        'generate-pass': {'user': user, 'password': password}
                    },
                    'nodeId': ''
                }
            }
        }
        try:
            index = int(NODE_INDEX)
        except:
            for node in nodes:
                body['options']['defaults']['graphOptions']['target'] = \
                    body['options']['defaults']['nodeId'] = \
                    node['id']
                _workflows.post_unbound_workflow('Graph.Bootstrap.With.BMC.Credentials.Setup', data=body, run_now=False)
            _workflows.run_workflow_tasks(None, DEFAULT_TIMEOUT_SEC)
            LOG.info('finished post bmc set')
            return
        # if node index is set
        body['options']['defaults']['graphOptions']['target'] = \
            body['options']['defaults']['nodeId'] = \
            nodes[index]['id']
        try:
            Api().nodes_workflow_action_by_id(nodes[index]['id'], {'command': 'cancel'})
        except ApiException as e:
            assert_equal(404, e.status, message='status should be 404')
        Api().workflows_post(body=body)
        log_context = self.__get_data().get('logContext')
        if log_context is None:
            raise Exception('Could not find logContext in {0}'.format(self.__get_data()))
            return
        # load graph instance id
        graph_instance = log_context.get('graphInstance')
        # LOG.info('graph instance {0}'.format(graph_instance))
        return self.__wait_for_completion(nodes[index], 'Graph.Bootstrap.With.BMC.Credentials.Setup', graph_instance)

    @test(enabled=True, groups=['ssh.connection.os.installed.test'])
    def validate_os_installed_test(self):
        """ Testing ssh connection to the installed OS"""
        delay = 10
        assert_true(self.check_ssh_connections(delay=delay), message="couldn't validate OS ssh connetion")

    @test(enabled=True, groups=['set.bmc.credentials.graph.test'], depends_on_groups=['ssh.connection.os.installed.test'])
    def set_bmc_credentials_workflow_test(self):
        self.__set_bmc_credentials(user=BMC_USER)
        LOG.info('Check if bmc user is been added')
        for node in self.__get_used_nodes():
            ipmi_resp = self.get_ipmi_user_list(node['id'])
            isfound = False
            for item in ipmi_resp.splitlines():
                if BMC_USER in item:
                    isfound = True
                    assert_true('ADMINISTRATOR' in item,
                                message='failed to create a {0} bmc user for node id {1}'.format(BMC_USER, node['id']))
            assert_equal(isfound, True,
                         message='failed to create a {0} bmc user for node id {1}'.format(BMC_USER, node['id']))

    @test(enabled=True, groups=['Decommission.graph.test'], depends_on_groups=['set.bmc.credentials.graph.test'])
    def decommission_workflow_test(self):
        """ Testing Decommissioning compute nodes"""
        body = {'options': {'remove-bmc-credentials': {'users': ['rackhd']}}}
        self.__post_workflow('Graph.Bootstrap.Decommission.Node', nodes=[], body=body)

    @test(enabled=True, groups=['remove.bmc.user.test'], depends_on_groups=['Decommission.graph.test'])
    def remove_bmc_user_test(self):
        """ Testing if decommission workflow removed bmc user from compute nodes"""
        for node in self.__get_used_nodes():
            ipmi_resp = self.get_ipmi_user_list(node['id'])
            for item in ipmi_resp.splitlines():
                if BMC_USER in item:
                    assert_false('ADMINISTRATOR' in item,
                                 message='failed to delete bmc user {0} for node id {1}'.format(BMC_USER, node['id']))

    @test(enabled=True, groups=['erase.disks.test'], depends_on_groups=['Decommission.graph.test'])
    def erase_disks_test(self):
        """ Testing if decommission graph erased the disks on the compute nodes"""
        LOG.info('Finally, check if disks is been deleted')
        is_deleted = self.check_ssh_connections(delay=10)
        assert_false(is_deleted, message='could not clear the disks')

    def check_ssh_connections(self, delay, nodes=[]):
        nodes_list = nodes if len(nodes) != 0 else self.__get_used_nodes()

        class ShhConnections():
            def __init__(self, host, username, password, nodeid):
                self.host = host
                self.username = username
                self.password = password
                self.node_id = nodeid
                self.is_up = False
                self.thread = None
                self.stopThread = None

        def worker(ssh_conn, delay):
            while True:
                try:
                    ssh = pxssh.pxssh()
                    ssh.login(ssh_conn.host, ssh_conn.username, ssh_conn.password)
                    ssh_conn.is_up = True
                    LOG.info('set it to True {0}'.format(ssh_conn.is_up))
                    return True
                except:
                    LOG.info('ssh login error for node {0}, hostname {1}'
                             .format(ssh_conn.node_id, ssh_conn.host))
                    time.sleep(delay)
                    pass
                if (ssh_conn.stopThread.is_set()):
                    break
            LOG.warning('could not connect to host {0} node id {1}'
                        .format(ssh_conn.host, ssh_conn.node_id))
            return False

        thread_list = []
        for node in nodes_list:
            hosts = self.__lookups_node_ip(node['id'])
            username = SSH_USER
            password = SSH_PASSWORD
            for host in hosts:
                os.popen("ssh-keygen -f ~/.ssh/known_hosts -R {0}".format(host))
                tmp = ShhConnections(host, username, password, node['id'])
                delay = 10
                tmp.stopThread = threading.Event()
                tmp.thread = threading.Thread(target=worker, args=(tmp, delay))
                thread_list.append(tmp)
        # start threading
        for item in thread_list:
            item.thread.start()
        # wait for threads to end
        for item in thread_list:
            item.thread.join(SSH_CONNECTION_TIMEOUT)
        # stop workers and check tests
        for item in thread_list:
            item.stopThread.set()
            if item.is_up is not True:
                return False
        return True
