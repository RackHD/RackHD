"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Initial test for checking the AMQPStreamMonitor listening capability.


Note: this can either be run using an "on-demand" docker based amqp
server OR using a "real" one.
For on-demand:
  python run_tests.py -stack vagrant -test \
     tests/framework_tsts/test_amqp_stream_monitor.py
For "real" server:
   python run_tests.py -stack vagrant -test \
     tests/framework_tsts/test_amqp_stream_monitor.py \
     --sm-amqp-url=amqp://user:password@localhost:9091

  The amqp-url has to use ports and credentials that have been setup
  inside the given amqp server.
"""
import fit_path  # NOQA: unused import
import unittest
import uuid
import json

# import nose decorator attr
from nose.plugins.attrib import attr

# Import the logging feature
import flogging
from sm_plugin import AMQPStreamMonitor

# set up the logging
logs = flogging.get_loggers()


@attr(regression=False, smoke=False, amqp_sm_framework=True)
class test_amqp_stream_monitor_framework(unittest.TestCase):
    longMessage = True

    def setUp(self):
        self.__amqp_sm = AMQPStreamMonitor()

    def shortDescription(self):
        # This removes the docstrings (""") from the unittest test list (collect-only)
        return None

    def test_amqp_sm_send_receive_sync_message(self):
        """ Send an amqp message and check it was correctly received """
        payload = {'test_uuid': str(uuid.uuid4())}
        queue = self.__amqp_sm.test_helper_sync_send_msg(
            'on.events', 'on.events', 'on.events.test', payload)
        got = self.__amqp_sm.test_helper_sync_recv_msg(queue)
        self.assertIsNotNone(got, "message never received")
        di = got.delivery_info
        self.assertEqual(di['routing_key'], 'on.events.test')
        body = json.loads(got.body)
        self.assertEqual(body['test_uuid'], payload['test_uuid'])

    def test_amqp_sm_send_receive_async_message(self):
        """ Send an amqp message and check it was correctly received via greenlet """
        on_events = self.__amqp_sm.get_queue_monitor('on.events', 'on.events.tests')
        expected = on_events.inject_test()
        got, body = on_events.wait_for_one_message()
        self.assertIsNotNone(got, "message never received")
        di = got.delivery_info
        body = json.loads(body)
        self.assertEqual(di['routing_key'], 'on.events.tests')
        self.assertEqual(body['test_uuid'], expected['payload']['test_uuid'])

    def test_amqp_sm_display_async_message(self):
        """ Send, receive, and display an AMQP message """
        on_events = self.__amqp_sm.get_queue_monitor('on.events', 'on.events.tests')
        on_events.inject_test()
        got, body = on_events.wait_for_one_message()
        self.assertIsNotNone(got, "message never received")
        di = got.delivery_info
        body = json.loads(body)
        logs.data_log.info('delivery_info from message=%s', di)
        logs.data_log.info('body from message=%s', body)

    def test_amqp_heartbeats(self):
        on_hb = self.__amqp_sm.get_queue_monitor('on.events', 'heartbeat.#')
        got, body = on_hb.wait_for_one_message(20)
        self.assertIsNotNone(got, "message never received")
        di = got.delivery_info
        body = json.loads(body)
        logs.data_log.info('RoutingKey: %s', di['routing_key'])
        logs.data_log.info('delivery_info from message=%s', di)
        logs.data_log.info('body from message=%s', body)

    def test_amqp_heartbeats_events(self):
        on_hb = self.__amqp_sm.get_queue_monitor('on.events', 'heartbeat.#')
        for x in range(6):
            got, body = on_hb.wait_for_one_message(20)
            self.assertIsNotNone(got, "message never received")
            di = got.delivery_info
            body = json.loads(body)
            logs.data_log.info('RoutingKey: %s', di['routing_key'])
            logs.data_log.info('delivery_info from message=%s', di)
            logs.data_log.debug('body from message=%s', body)


if __name__ == '__main__':
    unittest.main()
