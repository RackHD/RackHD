'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

This test will monitor amqp heartbeat message and validate the message format per latest notification event format
'''
import flogging
import fit_common
import unittest
from nose.plugins.attrib import attr
from sm_plugin import smp_get_stream_monitor

logs = flogging.get_loggers()


@attr(regression=False, smoke=False, amqp=True)
class TestAMQPHeartbeat(unittest.TestCase):
    longMessage = True

    @classmethod
    def setUpClass(cls):
        # Get the stream-monitor plugin for AMQP
        cls._amqp_sp = smp_get_stream_monitor('amqp')
        # Create the "all events" tracker
        cls._on_events_tracker = cls._amqp_sp.create_tracker('on-events-all', 'on.events', '#')

    def setUp(self):
        # attach a processor to the on-events-tracker amqp tracker. Then we can
        # attach indiviual match-clauses to this in each test-case.
        self.__proc = self._amqp_sp.get_tracker_queue_processor(self._on_events_tracker)

    def __common_on_x_heartbeat(self, service_name):
        rk = 'heartbeat.updated.information.#.{}'.format(service_name)
        self.__proc.match_on_routekey('all-heartbeats', routing_key=rk, max=3)
        results = self._amqp_sp.finish(timeout=20)
        results[0].assert_errors(self)
        first_event = self.__proc.get_raw_tracker_events()[0]
        expected_payload = {
            "type": "heartbeat",
            "action": "updated",
            "nodeId": 'null',
            "severity": "information",
            "version": "1.0"
        }
        self.__compare_heartbeat_message(first_event.body, expected_payload)

    def test_for_on_tftp_heartbeat(self):
        self.__common_on_x_heartbeat('on-tftp')

    def test_for_on_http_heartbeat(self):
        self.__common_on_x_heartbeat('on-http')

    def test_for_on_task_graph_heartbeat(self):
        self.__common_on_x_heartbeat('on-taskgraph')

    def test_for_on_syslog_heartbeat(self):
        self.__common_on_x_heartbeat('on-syslog')

    def test_for_on_dhcp_proxy_heartbeat(self):
        self.__common_on_x_heartbeat('on-dhcp-proxy')

    def __compare_heartbeat_message(self, amqp_body_json, expected_payload):
        try:
            self.assertEquals(
                amqp_body_json['version'], expected_payload['version'],
                "version field not correct! expect {0}, get {1}"
                .format(expected_payload['version'], amqp_body_json['version']))

            typeId_fields = amqp_body_json['typeId'].rsplit('.', 1)
            self.assertEquals(
                len(typeId_fields), 2,
                "The typeId '{}' of heartbeat should consists of <fqdn>.<service_name>".format(amqp_body_json['typeId']))
            service_name = typeId_fields[-1]
            self.assertIn(
                service_name, ['on-tftp', 'on-http', 'on-dhcp-proxy', 'on-taskgraph', 'on-syslog'],
                "service name is invalid!")
            self.assertEquals(
                amqp_body_json['action'], expected_payload['action'], "action field not correct!  expect {0}, get {1}"
                .format(expected_payload['action'], amqp_body_json['action']))
            self.assertEquals(
                amqp_body_json['severity'], expected_payload['severity'],
                "serverity field not correct!" .format(expected_payload['severity'], amqp_body_json['severity']))
            self.assertNotEquals(amqp_body_json['createdAt'], {}, "createdAt field is empty!")
            self.assertNotEquals(amqp_body_json['data'], {}, "data field is empty!")
        except KeyError as ex:
            self.fail("field '{}' missing from AMQP message".format(ex.args[0]))


if __name__ == '__main__':
    fit_common.unittest.main()
