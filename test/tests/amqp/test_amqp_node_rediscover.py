'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.
Author(s):
Norton Luo
This test validate the AMQP message send out in the workflow, and node delete and discover.
It also validate the web hook api and node registeration function.
Ths test will choose a node and reset it.  After the system start reset. It will delete the node and let the node
run into discover workflow. AMQP and webhook are lunched before that in separate working thread to monitor the messages.
'''

from time import sleep
import Queue
import random
import socket
import flogging
import logging
import pika
import unittest
import json
import threading
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import fit_common
import test_api_utils
from nose.plugins.attrib import attr
logs = flogging.get_loggers()
amqp_queue = Queue.Queue(maxsize=0)
webhook_port = 9889
nodefound_id = ""
webhook_received = False
webhook_body = ""


class AmqpWorker(threading.Thread):
    '''
    This AMQP worker Class will creat another thread when initialized and runs asynchronously.
    The external_callback is the callback function entrance for user.
    The callback function will be call when AMQP message is received.
    Each test case can define its own callback and pass the function name to the AMQP class.
    The timeout parameter specify how long the AMQP daemon will run. self.panic is called when timeout.
    eg:
    def callback(self, ch, method, properties, body):
        logs.debug(" [x] %r:%r" % (method.routing_key, body))
        logs.debug(" [x] %r:%r" % (method.routing_key, body))
    td = fit_amqp.AMQP_worker("node.added.#", callback)
    td.setDaemon(True)
    td.start()
    TODO:
    The common AMQP related test module of FIT is being refactoring. This AMQP test class is only for temporary use.
    It will be obsolete and replaced by a common AMQP test module.
    '''

    def __init__(self, exchange_name, topic_routing_key, external_callback, timeout=10):
        threading.Thread.__init__(self)
        pika_logger = logging.getLogger('pika')
        if fit_common.VERBOSITY >= 8:
            pika_logger.setLevel(logging.DEBUG)
        elif fit_common.VERBOSITY >= 4:
            pika_logger.setLevel(logging.WARNING)
        else:
            pika_logger.setLevel(logging.ERROR)
        if fit_common.API_PORT == 9090:
            amqp_port = fit_common.fitports()['amqp-vagrant']
        else:
            amqp_port = fit_common.fitports()['amqp']
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=fit_common.fitargs()["rackhd_host"], port=amqp_port))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=topic_routing_key)
        self.channel.basic_consume(external_callback, queue=queue_name)
        self.connection.add_timeout(timeout, self.dispose)

    def dispose(self):
        logs.debug_7('Pika connection timeout')
        if self.connection.is_closed is False:
            self.channel.stop_consuming()
            self.connection.close()
        self.thread_stop = True

    def run(self):
        logs.debug_7('start consuming')
        self.channel.start_consuming()


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        request_headers = self.headers
        content_length = request_headers.getheaders('content-length')
        length = int(content_length[0]) if content_length else 0
        global webhook_received, webhook_body
        webhook_received = True
        webhook_body = str(self.rfile.read(length))
        logs.debug(webhook_body)
        self.send_response(200)


class HttpWorker(threading.Thread):
    def __init__(self, port, timeout=10):
        threading.Thread.__init__(self)
        self.server = HTTPServer(('', port), RequestHandler)
        self.server.timeout = timeout

    def dispose(self):
        logs.debug('http service shutdown')
        self.thread_stop = True

    def run(self):
        self.server.handle_request()
        self.dispose()


@attr(all=True, regression=False, smoke=False)
class test_node_rediscover_amqp_message(unittest.TestCase):
    def setup(self):
        logs.debug_3('start rediscover')

    def teardown(self):
        logs.debug_3('finished rediscover')

    def _wait_for_discover(self, node_uuid):
        # start amqp thread
        timecount = 0
        while timecount < 600:
            if amqp_queue.empty() is False:
                check_message = amqp_queue.get()
                if check_message[0][0:10] == "node.added":
                    if self._wait_for_uuid(node_uuid):
                        self._process_message(
                            "added", check_message[1], check_message[1], "node", check_message)
                        global nodefound_id
                        nodefound_id = check_message[1]
                        return True
            sleep(1)
            timecount = timecount + 1
        logs.debug_2("Wait to rediscover Timeout!")
        return False

    def _set_web_hook(self, ip, port):
        mondata = fit_common.rackhdapi('/api/current/hooks')
        self.assertTrue(
            mondata['status'] < 209,
            'Incorrect HTTP return code, could not check hooks. expected<209, got:' + str(mondata['status']))
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

    def _apply_obmsetting_to_node(self, nodeid):
        # usr = ''
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
        if usr != "":
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

    def _node_registration_validate(self, amqp_body):
        try:
            amqp_body_json = json.loads(amqp_body)
        except ValueError:
            self.fail("FAILURE - The message body is not json format!")
        self.assertIn("nodeId", amqp_body_json["data"], "nodeId is not contained in the discover message")
        self.assertNotEquals(
            amqp_body_json["data"]["nodeId"], "", "nodeId generated in discovery doesn't include valid data ")
        self.assertIn(
            "ipMacAddresses", amqp_body_json["data"], "ipMacAddresses is not contained in the discover message")
        self.assertNotEquals(
            amqp_body_json["data"]["ipMacAddresses"], "",
            "ipMacAddresses generated during node discovery doesn't include valid data ")

    def _wait_for_uuid(self, node_uuid):
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
        logs.debug_3("Time out to find the node with uuid!")
        return False

    def _wait_amqp_message(self, timeout):
        timecount = 0
        while amqp_queue.empty() is True and timecount < timeout:
            sleep(1)
            timecount = timecount + 1
        self.assertNotEquals(
            timecount,
            timeout,
            "AMQP message receive timeout")

    def amqp_callback(self, ch, method, properties, body):
        logs.debug_3("Routing Key {0}:".format(method.routing_key))
        logs.data_log.debug_3(body.__str__())
        global amqp_queue, nodefound_id
        amqp_queue.put(
            [method.routing_key, fit_common.json.loads(body)["nodeId"], body])
        nodefound_id = fit_common.json.loads(body)["nodeId"]

    def _check_skupack(self):
        sku_installed = fit_common.rackhdapi('/api/2.0/skus')['json']
        if len(sku_installed) < 2:
            return False
        else:
            return True

    def _get_tester_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = fit_common.fitargs()['rackhd_host']
        logs.debug("pinging " + ip)
        s.connect((ip, 0))
        logs.debug('My IP address is: ' + s.getsockname()[0])
        return str(s.getsockname()[0])

    def _process_web_message(self, timeout):
        global webhook_received, webhook_body
        timecount = 0
        while webhook_received is False and timecount < timeout:
            sleep(1)
            timecount = timecount + 1
        self.assertNotEquals(timecount, timeout, "Web hook message receive timeout")
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

    def _process_message(self, action, typeid, nodeid, messagetype, amqp_message_body):
        expected_key = messagetype + "." + action + ".information." + typeid + "." + nodeid
        expected_payload = {
            "type": messagetype,
            "action": action,
            "typeId": typeid,
            "nodeId": nodeid,
            "severity": "information",
            "version": "1.0"}
        self._compare_message(amqp_message_body, expected_key, expected_payload)

    def _compare_message(self, amqpmessage, expected_key, expected_payload):
        routing_key = amqpmessage[0]
        amqp_body = amqpmessage[2]
        self.assertEquals(
            routing_key, expected_key, "Routing key is not expected! expect {0}, get {1}"
            .format(expected_key, routing_key))
        try:
            amqp_body_json = fit_common.json.loads(amqp_body)
        except ValueError:
            self.fail("FAILURE - The message body is not json format!")
        try:
            self.assertEquals(
                amqp_body_json['version'], expected_payload['version'],
                "version field not correct! expect {0}, get {1}"
                .format(expected_payload['version'], amqp_body_json['version']))
            self.assertEquals(
                amqp_body_json['typeId'], expected_payload['typeId'],
                "typeId field not correct!  expect {0}, get {1}"
                .format(expected_payload['typeId'], amqp_body_json['typeId']))
            self.assertEquals(
                amqp_body_json['action'], expected_payload['action'],
                "action field not correct!  expect {0}, get {1}"
                .format(expected_payload['action'], amqp_body_json['action']))
            self.assertEquals(
                amqp_body_json['severity'], expected_payload['severity'],
                "serverity field not correct!" .format(expected_payload['severity'], amqp_body_json['severity']))
            self.assertNotEquals(amqp_body_json['createdAt'], "", "createdAt field is empty!")
            self.assertNotEquals(amqp_body_json['data'], {}, "data field is empty!")
        except ValueError as e:
            self.fail("FAILURE - expected key is missing in the AMQP message!{0}".format(e))

    def _select_node(self):
        node_collection = test_api_utils.get_node_list_by_type("compute")
        self.assertNotEquals(node_collection, [], "No compute node found!")
        for dummy in node_collection:
            nodeid = node_collection[random.randint(0, len(node_collection) - 1)]
            if fit_common.rackhdapi('/api/2.0/nodes/' + nodeid)['json']['name'] != "Management Server":
                break
        return nodeid

    def _node_reboot(self, nodeid):
        # Reboot the node to begin rediscover.
        logs.debug_3('Running rediscover, resetting system node...')
        logs.debug('launch AMQP thread')
        reset_worker = AmqpWorker(
            exchange_name="on.events", topic_routing_key="graph.#." + nodeid,
            external_callback=self.amqp_callback, timeout=100)
        reset_worker.setDaemon(True)
        reset_worker.start()

        # Reboot the node, wait reboot workflow start message.
        response = fit_common.rackhdapi(
            '/redfish/v1/Systems/' + nodeid + '/Actions/ComputerSystem.Reset', action='post',
            payload={"reset_type": "ForceRestart"})
        self.assertTrue(
            response['status'] < 209, 'Incorrect HTTP return code, expected<209, got:' + str(response['status']))
        graphid = response['json']["@odata.id"].split('/redfish/v1/TaskService/Tasks/')[1]

        # wait for workflow started message.
        self._wait_amqp_message(10)
        workflow_amqp = amqp_queue.get()
        if workflow_amqp[0][0:14] == "started":
            self._process_message("started", graphid, nodeid, "graph", workflow_amqp)
        else:
            self._process_message("progress.updated", graphid, nodeid, "graph", workflow_amqp)

        # wait for progress update finish message.
        self._wait_amqp_message(10)
        workflow_amqp = amqp_queue.get()
        self._process_message("progress.updated", graphid, nodeid, "graph", workflow_amqp)

        # wait for progress finish message.
        retry_count = 0
        while retry_count < 10:
            self._wait_amqp_message(60)
            workflow_amqp = amqp_queue.get()
            if workflow_amqp[0][0:14] == "graph.finished":
                self._process_message("finished", graphid, nodeid, "graph", workflow_amqp)
                break
            retry_count = retry_count + 1
        self.assertNotEquals(retry_count, 10, "No AMQP workflow finished message received")
        reset_worker.dispose()

    def _node_delete(self, nodeid):
        logs.debug('launch node delete AMQP thread')
        td = AmqpWorker(
            exchange_name="on.events", topic_routing_key="node.#.information." + nodeid + ".#",
            external_callback=self.amqp_callback, timeout=30)
        td.setDaemon(True)
        td.start()
        result = fit_common.rackhdapi('/api/2.0/nodes/' + nodeid, action='delete')
        self.assertTrue(result['status'] < 209, 'Was expecting response code < 209. Got ' + str(result['status']))
        self._wait_amqp_message(10)
        amqp_message = amqp_queue.get()
        self._process_message("removed", nodeid, nodeid, "node", amqp_message)
        td.dispose()

    def _node_discover(self, node_uuid):
        # start discovery
        logs.debug_2("Waiting node reboot and boot into microkernel........")
        myip = self._get_tester_ip()
        self._set_web_hook(myip, webhook_port)
        logs.debug('Listening on localhost:%s' % webhook_port)
        global webhook_received
        webhook_received = False
        serverworker = HttpWorker(webhook_port, 300)
        serverworker.setDaemon(True)
        serverworker.start()

        # clear the amqp message queue
        while amqp_queue.empty is False:
            amqp_queue.get()

        logs.debug('launch AMQP thread for discovery')
        discover_worker = AmqpWorker(
            exchange_name="on.events", topic_routing_key="node.#.information.#", external_callback=self.amqp_callback,
            timeout=600)
        discover_worker.setDaemon(True)
        discover_worker.start()

        logs.debug('Wait for node added')
        # use the original node's UUID to verify the node discovered is the one we just deleted.
        self.assertTrue(self._wait_for_discover(node_uuid), "Fail to find the orignial node after reboot!")
        logs.debug_2("Found the original node. It is rediscovered successfully!")

        logs.debug('Wait for node discovery')
        self._wait_amqp_message(60)
        amqp_message_discover = amqp_queue.get()
        self._process_message("discovered", nodefound_id, nodefound_id, "node", amqp_message_discover)

        logs.debug('Validate node discovery registration AMQP Message')
        self._node_registration_validate(amqp_message_discover[2])
        logs.debug('Validate node discovery registration web hook Message')
        self._process_web_message(30)

        # skip sku.assigned message if no skupack is installed on RackHD
        skupack_intalled = self._check_skupack()
        if skupack_intalled:
            logs.debug_2("wait for skupack assign!")
            self._wait_amqp_message(50)
            amqp_message_discover = amqp_queue.get()
            self._process_message("sku.assigned", nodefound_id, nodefound_id, "node", amqp_message_discover)
        else:
            logs.warning("skupack is not installed, skip sku assigned message check!")
        logs.debug_3("wait for obm assign!")

        # re-apply obm setting to the node to generate obm.assigned message
        self.assertTrue(self._apply_obmsetting_to_node(nodefound_id), "Fail to apply obm setting!")
        self._wait_amqp_message(50)
        amqp_message_discover = amqp_queue.get()
        self._process_message("obms.assigned", nodefound_id, nodefound_id, "node", amqp_message_discover)
        logs.debug_3("wait for accessible!")
        self._wait_amqp_message(100)
        amqp_message_discover = amqp_queue.get()
        self._process_message("accessible", nodefound_id, nodefound_id, "node", amqp_message_discover)
        discover_worker.dispose()

    def test_rediscover(self):
        nodeid = self._select_node()
        logs.debug_2('Checking OBM setting...')
        node_obm = fit_common.rackhdapi('/api/2.0/nodes/' + nodeid)['json']['obms']
        if node_obm == []:
            self.assertTrue(self._apply_obmsetting_to_node(nodeid), "Fail to apply obm setting!")
        node_uuid = fit_common.rackhdapi('/redfish/v1/Systems/' + nodeid)['json']['UUID']
        logs.debug_3('UUID of selected Node is:{}'.format(node_uuid))
        self._node_reboot(nodeid)
        self._node_delete(nodeid)
        self._node_discover(node_uuid)


if __name__ == '__main__':
    unittest.main()
