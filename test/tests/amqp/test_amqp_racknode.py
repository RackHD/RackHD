'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo

'''
import json
from time import sleep
import json
import string
from datetime import *
import threading
import pika
import logging
import flogging
import fit_path
import fit_common
import test_api_utils
from nose.plugins.attrib import attr

amqp_message_received = False
routing_key = ""
amqp_body = ""
logs = flogging.get_loggers()


class AmqpWorker(threading.Thread):
    '''
    This AMQP worker Class will creat another thread when initialized and runs asynchronously.
    The externalcallback is the callback function entrance for user.
    The callback function will be call when AMQP message is received.
    Each test case can define its own callback and pass the function name to the AMQP class.
    The timeout parameter specify how long the AMQP daemon will run. self.panic is called when timeout.
    eg:
    def callback(self, ch, method, properties, body):
        logs.debug(" [x] %r:%r" % (method.routing_key, body))
        print(" [x] %r:%r" % (method.routing_key, body))

    td = fit_amqp.AMQP_worker("node.added.#", callback)
    td.setDaemon(True)
    td.start()
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
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=fit_common.fitargs()["ora"], port=fit_common.fitports()['amqp']))
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=topic_routing_key)
        self.channel.basic_consume(external_callback, queue=queue_name)
        self.connection.add_timeout(timeout, self.panic)

    def panic(self):
        self.channel.stop_consuming()
        if fit_common.VERBOSITY >= 4:
            print 'Pika connection timeout'
        self.connection.close()
        exit(0)

    def run(self):
        if fit_common.VERBOSITY >= 4:
            print 'start consuming'
        self.channel.start_consuming()


@attr(all=True, regression=True, smoke=True)
class amqp_rack_node(fit_common.unittest.TestCase):
    # clear the test environment
    def tear_down(self):
        self.test_api_delete_rack()

    def _compare_message(self, expected_key, expected_payload):
        global routing_key, amqp_body
        self.assertEquals(
            routing_key, expected_key, "Routing key is not expected! expect {0}, get{1}"
            .format(expected_key, routing_key))
        try:
            amqp_body_json = fit_common.json.loads(amqp_body)
        except:
            logs.error("FAILURE - The message body is not json format!")
            return False
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
                "serverity field not correct!"
                .format(expected_payload['severity'], amqp_body_json['severity']))
            self.assertNotEquals(amqp_body_json['createdAt'], {}, "createdAt field is empty!")
            self.assertNotEquals(amqp_body_json['data'], {}, "data field is empty!")
        except ValueError:
            logs.error("FAILURE - expected key is missing in the AMQP message!")
            return False
        return True

    def amqp_callback(self, ch, method, properties, body):
        logs.debug_3("Routing Key %r:" % method.routing_key)
        logs.debug_3(body.__str__())
        global amqp_message_received
        global routing_key, amqp_body
        amqp_message_received = True
        amqp_body = body
        routing_key = method.routing_key

    def test_api_create_and_check_racks(self):
        logs.debug_2("Going to generate 10 rack nodes to trigger AMQP message")
        for operator in range(0, 10):
            rackname = "myRack" + "_" + datetime.now().__str__()
            newrack = {"name": rackname, "type": "rack"}
            logs.debug_3(" Create New Tag %r" % newrack)
            mon_url = '/api/2.0/nodes'
            # start amqp thread
            global amqp_message_received
            amqp_message_received = False
            logs.debug('launch AMQP thread')
            td = AmqpWorker(
                exchange_name="on.events", topic_routing_key="node.added.#",
                external_callback=self.amqp_callback, timeout=10)
            td.setDaemon(True)
            td.start()
            mon_data_post = fit_common.rackhdapi(mon_url, action='post', payload=newrack)
            self.assertIn(
                mon_data_post['status'], range(200, 205),
                "Incorrect HTTP return code: {}".format(mon_data_post['status']))
            rackid = mon_data_post['json']['id']
            mon_url = '/api/2.0/nodes/{}'.format(rackid)
            mon_data = fit_common.rackhdapi(mon_url)
            self.assertIn(
                mon_data['status'], range(200, 205),
                "Incorrect HTTP return code: {}".format(mon_data['status']))
            json_node_data = mon_data['json']
            self.assertTrue(
                json_node_data['name'] == newrack['name'] and json_node_data['type'] == "rack",
                "rack node field error")
            timecount = 0
            while amqp_message_received is False and timecount < 10:
                sleep(1)
                timecount = timecount + 1
            self.assertNotEquals(timecount, 10, "No AMQP message received")
            expected_key = "node.added.information." + rackid + '.' + rackid
            expected_payload = {
                "type": "node",
                "action": "added",
                "typeId": rackid,
                "nodeId": rackid,
                "severity": "information",
                "version": "1.0",
                "createdAt": mon_data_post['json']['createdAt']}
            self.assertEquals(self._compare_message(expected_key, expected_payload), True, "AMQP Message Check Error!")
            logs.debug_3("query rack: %r successfully!" % rackname)
        if fit_common.VERBOSITY >= 2:
            print "test: rack creation and query succeed!"

    def test_api_delete_rack(self):
        rack_node_list = test_api_utils.get_node_list_by_type("rack")
        for rack in rack_node_list:
            global amqp_message_received
            amqp_message_received = False
            # start amqp thread
            td = AmqpWorker(
                exchange_name="on.events", topic_routing_key="node.removed.#",
                external_callback=self.amqp_callback, timeout=10)
            td.setDaemon(True)
            td.start()
            mon_url = '/api/2.0/nodes/{}'.format(rack)
            mon_data = fit_common.rackhdapi(mon_url, action='delete')
            self.assertIn(
                mon_data['status'], range(200, 205),
                "Incorrect HTTP return code: {}".format(mon_data['status']))
            timecount = 0
            while amqp_message_received is False and timecount < 10:
                sleep(1)
                timecount = timecount + 1
            self.assertNotEquals(timecount, 10, "No AMQP message received")
            expected_key = "node.removed.information." + rack + '.' + rack
            expected_payload = {
                "type": "node",
                "action": "removed",
                "typeId": rack,
                "nodeId": rack,
                "severity": "information",
                "version": "1.0",
                "createdAt": mon_data['headers']['Date']}
            self.assertEquals(self._compare_message(expected_key, expected_payload), True, "AMQP Message Check Error!")


if __name__ == '__main__':
    fit_common.unittest.main()
