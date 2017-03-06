'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo

'''
from time import sleep
import threading
import pika
import logging
import flogging
import fit_common
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
        logs.debug(" [x] %r:%r" % (method.routing_key, body))

    td = fit_amqp.AMQP_worker("node.added.#", callback)
    td.setDaemon(True)
    td.start()
    '''

    def __init__(
            self,
            exchange_name,
            topic_routing_key,
            external_callback,
            timeout=10):
        threading.Thread.__init__(self)
        pika_logger = logging.getLogger('pika')
        if fit_common.VERBOSITY >= 8:
            pika_logger.setLevel(logging.DEBUG)
        elif fit_common.VERBOSITY >= 4:
            pika_logger.setLevel(logging.WARNING)
        else:
            pika_logger.setLevel(logging.ERROR)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=fit_common.fitargs()["rackhd_host"],
                port=fit_common.fitports()['amqp']))
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
        logs.debug_7('Pika connection timeout')
        self.connection.close()
        exit(0)

    def run(self):
        logs.debug_7('start consuming')
        self.channel.start_consuming()


@attr(all=True, regression=True, smoke=True)
class amqp_heartbeat(fit_common.unittest.TestCase):
    # clear the test environment

    def _compare_heartbeat_message(self, expected_key, expected_payload):
        global routing_key, amqp_body
        assert expected_key in routing_key, (expected_key, routing_key)
        try:
            amqp_body_json = fit_common.json.loads(amqp_body)
        except:
            logs.error("FAILURE - The message body is not json format!")
            return False
        try:
            self.assertEquals(
                amqp_body_json['version'],
                expected_payload['version'],
                "version field not correct! expect {0}, get {1}" .format(
                    expected_payload['version'],
                    amqp_body_json['version']))

            typeId_fields = amqp_body_json['typeId'].split('.')
            assert len(
                typeId_fields) == 2, "The typeId of heartbeat should consists of <fqdn>.<service_name>"
            service_name = typeId_fields[-1]
            assert service_name in [
                'on-tftp',
                'on-http',
                'on-dhcp-proxy',
                'on-taskgraph',
                'on-syslog']
            self.assertEquals(
                amqp_body_json['action'], expected_payload['action'],
                "action field not correct!  expect {0}, get {1}"
                .format(expected_payload['action'], amqp_body_json['action']))
            self.assertEquals(
                amqp_body_json['severity'],
                expected_payload['severity'],
                "serverity field not correct!" .format(
                    expected_payload['severity'],
                    amqp_body_json['severity']))
            self.assertNotEquals(
                amqp_body_json['createdAt'],
                {},
                "createdAt field is empty!")
            self.assertNotEquals(
                amqp_body_json['data'],
                {},
                "data field is empty!")
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

    def test_amqp_hearbeat_message(self):
        # start amqp thread
        global amqp_message_received
        amqp_message_received = False
        logs.debug('launch AMQP thread')

        td = AmqpWorker(
            exchange_name="on.events",
            topic_routing_key="heartbeat.updated.information.#",
            external_callback=self.amqp_callback,
            timeout=10)
        td.setDaemon(True)
        td.start()
        timecount = 0
        while amqp_message_received is False and timecount < 10:
            sleep(1)
            timecount = timecount + 1
            if amqp_message_received:
                break
            self.assertNotEquals(timecount, 10, "No AMQP message received")

        expected_sub_key = "heartbeat.updated.information."
        expected_payload = {
            "type": "heartbeat",
            "action": "updated",
            "nodeId": 'null',
            "severity": "information",
            "version": "1.0"
        }
        self.assertEquals(
            self._compare_heartbeat_message(
                expected_sub_key,
                expected_payload),
            True,
            "AMQP Message Check Error!")


if __name__ == '__main__':
    fit_common.unittest.main()
