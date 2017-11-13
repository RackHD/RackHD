'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo
This test validate the AMQP message send out in the workflow, and node delete and discover.
It also validate the web hook api and node registeration function.
Ths test will choose a node and reset it.  After the system start reset. It will delete the node and let the node
run into discover workflow. AMQP and webhook are lunched before that in separate working thread to monitor the messages.
'''

from sm_plugin import smp_get_stream_monitor
from time import sleep
import gevent
import gevent.queue
import random
import flogging
import unittest
import json
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import fit_common
import env_ip_helpers
import test_api_utils
from nose.plugins.attrib import attr
from nosedep import depends

logs = flogging.get_loggers()
WEBHOOK_PORT = 9889


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        logs.debug('POST came in on test-http-server')
        request_headers = self.headers
        content_length = request_headers.getheaders('content-length')
        if content_length:
            length = int(content_length[0])
        else:
            length = 0

        webhook_body = str(self.rfile.read(length))
        logs.tdl.debug('body is: %s', webhook_body)
        self.send_response(200)
        self.server.do_post_queue.put(webhook_body)


class HttpWorker(gevent.Greenlet):
    def __init__(self, port, timeout=10):
        super(HttpWorker, self).__init__()
        self.__server = HTTPServer(('', port), RequestHandler)
        self.__server.timeout = timeout
        self.__server.do_post_queue = gevent.queue.Queue()
        testhost_ipv4 = env_ip_helpers.get_testhost_ip()
        self.ipv4_address = testhost_ipv4
        self.ipv4_port = port

    @property
    def do_post_queue(self):
        return self.__server.do_post_queue

    def dispose(self):
        logs.debug('http service shutdown')

    def _run(self):
        self.__server.handle_request()


@attr(all=True, regression=False, smoke=False)
class test_node_rediscover_amqp_message(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Get the stream-monitor plugin for AMQP
        cls._amqp_sp = smp_get_stream_monitor('amqp')
        # Create the "all events" tracker
        cls._on_events_tracker = cls._amqp_sp.create_tracker('on-events-all', 'on.events', '#')
        # We have context information that needs to be passed from test-to-test. Set up the template
        # space.
        cls._run_context = {
            'start_nodeid': None,
            'start_node_uuid': None,
            'reboot_graphid': None,
            'rediscovered_nodeid': None
        }

        # Set up the web-serverlet to get the callback from the hooks part
        # of the api. We do this here so thee server stays up for the required
        # tests!
        cls._serverworker = HttpWorker(WEBHOOK_PORT, 300)
        cls._serverworker.start()

    @classmethod
    def tearDownClass(cls):
        cls._serverworker.dispose()

    def setUp(self):
        # attach a processor to the on-events-tracker amqp tracker. Then we can
        # attach indiviual match-clauses to this in each test-case.
        self.__qproc = self._amqp_sp.get_tracker_queue_processor(self._on_events_tracker)

    def __set_run_context(self, key, value):
        assert key in self._run_context, \
            '{} not a run-context variable'.format(key)
        assert self._run_context[key] is None, \
            'attempt to set existing run-context for {} to {}, was already {}'.format(
                key, value, self._run_context[key])
        self._run_context[key] = value

    def __get_run_context(self, key):
        assert key in self._run_context, \
            '{} not a run-context variable'.format(key)
        assert self._run_context[key] is not None, \
            'attempt to get unset run-context for {}'.format(key)
        return self._run_context[key]

    def __set_web_hook(self):
        mondata = fit_common.rackhdapi('/api/current/hooks')
        self.assertTrue(
            mondata['status'] < 209,
            'Incorrect HTTP return code, could not check hooks. expected<209, got:' + str(mondata['status']))
        ip = self._serverworker.ipv4_address
        # ip = '172.31.110.34'
        port = self._serverworker.ipv4_port
        hookurl = "http://" + str(ip) + ":" + str(port)
        for hooks in mondata['json']:
            if hooks['url'] == hookurl:
                logs.debug("Hook URL already exist in RackHD")
                return
        response = fit_common.rackhdapi(
            '/api/current/hooks',
            action='post',
            payload={
                "name": "FITdiscovery",
                "url": hookurl,
                "filters": [{"type": "node",
                            "action": "discovered"}]})
        self.assertTrue(
            response['status'] < 209,
            'Incorrect HTTP return code, expected<209, got:' + str(response['status']))

    def __apply_obmsetting_to_node(self, nodeid):
        usr = None
        # pwd = ''
        response = fit_common.rackhdapi(
            '/api/2.0/nodes/' + nodeid + '/catalogs/bmc')
        bmcip = response['json']['data']['IP Address']
        # Try credential record in config file
        for creds in fit_common.fitcreds()['bmc']:
            if fit_common.remote_shell(
                'ipmitool -I lanplus -H ' + bmcip + ' -U ' + creds['username'] + ' -P ' +
                    creds['password'] + ' fru')['exitcode'] == 0:
                usr = creds['username']
                pwd = creds['password']
                break
        # Put the credential to OBM settings
        if usr is not None:
            payload = {
                "service": "ipmi-obm-service",
                "config": {
                    "host": bmcip,
                    "user": usr,
                    "password": pwd},
                "nodeId": nodeid}
            api_data = fit_common.rackhdapi("/api/2.0/obms", action='put', payload=payload)
            if api_data['status'] == 201:
                return True
        return False

    def __check_skupack(self):
        sku_installed = fit_common.rackhdapi('/api/2.0/skus')['json']
        if len(sku_installed) < 2:
            return False
        else:
            return True

    def __process_web_message(self, webhook_body):
        try:
            webhook_body_json = json.loads(webhook_body)
        except ValueError:
            self.fail("FAILURE - The message body is not json format!")

        self.assertIn("action", webhook_body_json, "action field is not contained in the discover message")
        self.assertEquals(
            webhook_body_json['action'], "discovered",
            "action field not correct!  expect {0}, get {1}"
            .format("discovered", webhook_body_json['action']))
        self.assertIn("data", webhook_body_json, "data field is not contained in the discover message")
        self.assertIn("nodeId", webhook_body_json["data"], "nodeId is not contained in the discover message")
        self.assertNotEquals(
            webhook_body_json["data"]["nodeId"], "", "nodeId generated in discovery doesn't include valid data ")
        self.assertIn(
            "ipMacAddresses", webhook_body_json["data"], "ipMacAddresses is not contained in the discover message")
        self.assertNotEquals(
            webhook_body_json["data"]["ipMacAddresses"], "",
            "ipMacAddresses generated during node discovery doesn't include valid data ")

    def __build_info_vblock(self, message_type, action, typeid, nodeid):
        expected_payload = {
            "type": message_type,
            "action": action,
            "typeId": typeid,
            "nodeId": nodeid,
            "severity": "information",
            "createdAt": "<<present>>",
            "data": "<<present>>",
            "version": "1.0"
        }
        expected_rk = "{}.{}.information.{}.{}".format(message_type, action, typeid, nodeid)
        ex = {
            'body': expected_payload,
            'routing_key': expected_rk
        }
        return ex

    def __build_simple_graph_vblock(self, action, graphid, status):
        ex = {
            'body': {
                'status': status
            },
            'routing_key': 'graph.{}.{}'.format(action, graphid)
        }
        return ex

    def __wait_for_uuid(self):
        node_uuid = self.__get_run_context('start_node_uuid')
        logs.debug('Begining wait for uuid %s to reappear', node_uuid)
        for dummy in range(0, 20):
            sleep(30)
            rest_data = fit_common.rackhdapi('/redfish/v1/Systems/')
            if rest_data['json']['Members@odata.count'] == 0:
                continue
            node_collection = rest_data['json']['Members']
            for computenode in node_collection:
                nodeidurl = computenode['@odata.id']
                api_data = fit_common.rackhdapi(nodeidurl)
                if api_data['status'] > 399:
                    break
                if node_uuid == api_data['json']['UUID']:
                    return True
        logs.debug("Time out to find the node with uuid!")
        return False

    def __check_added_node_CB(self, other_event):
        body = other_event.body
        if "nodeId" not in body:
            return False
        new_nodid = body["nodeId"]
        if self.__wait_for_uuid():
            self.__set_run_context('rediscovered_nodeid', new_nodid)
            logs.debug('Located node again with id=%s', new_nodid)
            return True
        return False

    def __node_discover(self, node_uuid):
        logs.debug('Validate node discovery registration web hook Message')
        self._process_web_message(30)

    def test_rediscover_pick_node(self):
        node_collection = test_api_utils.get_node_list_by_type("compute")
        self.assertNotEquals(node_collection, [], "No compute node found!")
        for dummy in node_collection:
            nodeid = node_collection[random.randint(0, len(node_collection) - 1)]
            if fit_common.rackhdapi('/api/2.0/nodes/' + nodeid)['json']['name'] != "Management Server":
                break
        self.__set_run_context('start_nodeid', nodeid)
        node_uuid = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid)['json']['UUID']
        logs.debug('UUID of selected Node is %s', node_uuid)
        self.__set_run_context('start_node_uuid', node_uuid)

    @depends(after='test_rediscover_pick_node')
    def test_rediscover_check_obm(self):
        nodeid = self.__get_run_context('start_nodeid')
        node_obm = fit_common.rackhdapi('/api/2.0/nodes/' + nodeid)['json']['obms']
        if node_obm == []:
            logs.trl.debug('Picked node does not have OBM settings. Trying to add them')
            applied = self.__apply_obmsetting_to_node(self.__get_run_context('start_nodeid'))
            self.assertTrue(applied, 'Failed to apply obm settings')

    @depends(after='test_rediscover_check_obm')
    def test_rediscover_reboot_kickoff(self):
        nodeid = self.__get_run_context('start_nodeid')
        # first setup the web-hook to monitor (see test_rediscover_rackd_discover_hook) for
        # rackhd hook messages.
        self.__set_web_hook()
        # now give the node a kick
        response = fit_common.rackhdapi(
            '/redfish/v1/Systems/' + nodeid + '/Actions/ComputerSystem.Reset', action='post',
            payload={"ResetType": "ForceRestart"})
        self.assertTrue(
            response['status'] < 209, 'Incorrect HTTP return code, expected<209, got:' + str(response['status']))
        graphid = response['json']["@odata.id"].split('/redfish/v1/TaskService/Tasks/')[1]
        self.__set_run_context('reboot_graphid', graphid)

    @depends(after='test_rediscover_reboot_kickoff', before='test_rediscover_node_delete')
    def test_rediscover_reboot_graph_ampq_flow(self):
        nodeid = self.__get_run_context('start_nodeid')
        graphid = self.__get_run_context('reboot_graphid')
        # Push a new match-group onto this processor. Ordered=true makes it so the the matchers
        # in it need to occur in order.
        self.__qproc.open_group(ordered=True)
        self.__qproc.match_on_routekey('basic-start', routing_key='graph.started.{}'.format(graphid),
                                       validation_block=self.__build_simple_graph_vblock('started', graphid, 'running'))
        self.__qproc.match_on_routekey('info-start', routing_key='graph.started.information.{}.#'.format(graphid),
                                       validation_block=self.__build_info_vblock('graph', 'started', graphid, nodeid))
        # note: the (3,4) bounding here is actually there because of a flaw in the and-group matcher.
        #  it's a sticky enough thing to fix, so I'm letting it go for now. Basically, what
        #  happens is we get 3 progress messages, the basic-finish, and one more progress. But
        #  if we call out the 4th one as its own matcher (and put 3,3 here), this
        #  one overmatches.
        self.__qproc.match_on_routekey('graph-task-progress',
                                       routing_key='graph.progress.updated.information.{}.#'.format(graphid),
                                       min=3, max=4,
                                       validation_block=self.__build_info_vblock('graph', 'progress.updated', graphid, nodeid))

        self.__qproc.match_on_routekey(description='basic-finish', routing_key='graph.finished.{}'.format(graphid),
                                       validation_block=self.__build_simple_graph_vblock('finished', graphid, 'succeeded'))
        self.__qproc.match_on_routekey(description='info-finish', routing_key='graph.finished.information.{}.#'.format(graphid),
                                       validation_block=self.__build_info_vblock('graph', 'finished', graphid, nodeid))
        self.__qproc.close_group()

        results = self._amqp_sp.finish(timeout=30)
        results[0].assert_errors(self)

    @depends(after='test_rediscover_reboot_kickoff')
    def test_rediscover_node_delete(self):
        nodeid = self.__get_run_context('start_nodeid')
        result = fit_common.rackhdapi('/api/2.0/nodes/' + nodeid, action='delete')
        self.assertTrue(result['status'] < 209, 'Was expecting response code < 209. Got ' + str(result['status']))
        self.__qproc.match_on_routekey('node-removed-information',
                                       routing_key='node.removed.information.{}.#'.format(nodeid),
                                       validation_block=self.__build_info_vblock('node', 'removed', nodeid, nodeid))

        results = self._amqp_sp.finish(timeout=30)
        results[0].assert_errors(self)

    @depends(after='test_rediscover_node_delete')
    def test_rediscover_node_discover_rebooted_node(self):
        # look for node-adds until one happens that has the same uuid as the old deleted node
        self.__qproc.match_on_routekey('node-added', routing_key='node.added.#', match_CB=self.__check_added_node_CB)
        results = self._amqp_sp.finish(timeout=300)
        results[0].assert_errors(self)

    @depends(after='test_rediscover_node_discover_rebooted_node', before='test_rediscover_node_registration')
    def test_rediscover_node_discover_sku_assign(self):
        nodeid = self.__get_run_context('rediscovered_nodeid')
        skupack_intalled = self.__check_skupack()
        if not skupack_intalled:
            raise unittest.SkipTest('skupack is not installed, skipping sku assigned message check')

        self.__qproc.match_on_routekey('sku-assigned', routing_key='node.sku.assigned.information.{}.#'.format(nodeid),
                                       validation_block=self.__build_info_vblock('node', 'sku.assigned', nodeid, nodeid))
        results = self._amqp_sp.finish(timeout=300)
        results[0].assert_errors(self)

    @depends(after='test_rediscover_node_discover_rebooted_node')
    def test_rediscover_node_registration(self):
        nodeid = self.__get_run_context('rediscovered_nodeid')
        self.__qproc.match_on_routekey('node-discovered-information',
                                       routing_key='node.discovered.information.{}.#'.format(nodeid),
                                       validation_block=self.__build_info_vblock('node', 'discovered', nodeid, nodeid))
        results = self._amqp_sp.finish(timeout=300)
        results[0].assert_errors(self)

    @depends(after='test_rediscover_node_registration')
    def test_rediscover_rackd_discover_hook(self):
        found_msgs = []
        while True:
            try:
                m = self._serverworker.do_post_queue.get(timeout=0.1)
            except gevent.queue.Empty:
                m = None
            if m is None:
                break
            self.__process_web_message(m)
            found_msgs.append(m)

        found_count = len(found_msgs)
        self.assertNotEqual(found_count, 0, 'No discovery message was posted back via the webhook')
        self.assertEqual(found_count, 1, 'Received more than one posted webhook: {}'.format(found_msgs))

    @depends(after='test_rediscover_node_registration')
    def test_rediscover_node_discover_obm_settings(self):
        nodeid = self.__get_run_context('rediscovered_nodeid')
        applied = self.__apply_obmsetting_to_node(nodeid)
        self.assertTrue(applied, 'failed to apply obm settings to rediscovered node {}'.format(nodeid))

        self.__qproc.match_on_routekey('obm-assigned', routing_key='node.obms.assigned.information.{}.#'.format(nodeid),
                                       validation_block=self.__build_info_vblock('node', 'obms.assigned', nodeid, nodeid))
        self.__qproc.match_on_routekey('node-accessible', routing_key='node.accessible.information.{}.#'.format(nodeid),
                                       validation_block=self.__build_info_vblock('node', 'accessible', nodeid, nodeid))

        results = self._amqp_sp.finish(timeout=300)
        results[0].assert_errors(self)


if __name__ == '__main__':
    unittest.main()
