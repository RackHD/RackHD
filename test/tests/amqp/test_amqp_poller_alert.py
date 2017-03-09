'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo
This test validate the amqp message alert send out from RackHD by monitor SEL log poller and power state poller. The
AMQP message should comply to the latest event notification spec.
The SEL log poller test will inject a CPU IERR event in the node BMC by ipmitool. RackHD should detect this sel entry
and generate an AMQP alert message.
The power state poller test will use ipmitool to change the system chassis power state. And RackHD is expected to detect
such event by chassis power poller and sent out AMQP event notification.
'''

from time import sleep
import Queue
import random
import flogging
import logging
import pika
import unittest
import threading
import fit_common
import test_api_utils
from nose.plugins.attrib import attr
logs = flogging.get_loggers()
amqp_queue = Queue.Queue(maxsize=0)
nodefound_id = ""


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
        if fit_common.API_PORT == 9090:
            amqp_port = fit_common.fitports()['amqp-vagrant']
        else:
            amqp_port = fit_common.fitports()['amqp']
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=fit_common.fitargs()["rackhd_host"],
                port=amqp_port))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=topic_routing_key)
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


# Check if the node is rediscovered. Retry in every 30 seconds and total
# 600 seconds.
@attr(all=True, regression=False, smoke=False)
class test_poller_alert_amqp_message(unittest.TestCase):

    def setup(self):
        logs.debug_3('start rediscover')

    def teardown(self):
        logs.debug_3('finished rediscover')

    def _apply_obmsetting_to_node(self, nodeid):
        usr = ''
        pwd = ''
        response = fit_common.rackhdapi(
            '/api/2.0/nodes/' + nodeid + '/catalogs/bmc')
        bmcip = response['json']['data']['IP Address']
        # Try credential record in config file
        for creds in fit_common.fitcreds()['bmc']:
            if fit_common.remote_shell(
                'ipmitool -I lanplus -H ' +
                bmcip +
                ' -U ' +
                creds['username'] +
                ' -P ' +
                creds['password'] +
                    ' fru')['exitcode'] == 0:
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
            api_data = fit_common.rackhdapi(
                "/api/2.0/obms", action='put', payload=payload)
            if api_data['status'] == 201:
                return True
        return False, bmcip

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

    def _get_ipmi_poller_by_node(self, node_id, seltype):
        monurl = "/api/2.0/nodes/" + str(node_id) + "/pollers"
        mondata = fit_common.rackhdapi(url_cmd=monurl)
        if mondata['status'] not in [200, 201, 202, 204]:
            self.fail("Get status: {},  Failed to get pollers for node: {}".format(mondata['status'], node_id))
        else:
            pollers = mondata['json']
            for poller in pollers:
                if poller["config"]["command"] == seltype:
                    return poller["id"]
        self.fail("Fail to find out ipmi poller")

    def amqp_callback(self, ch, method, properties, body):
        logs.debug_3("Routing Key {0}:".format(method.routing_key))
        logs.data_log.debug_3(body.__str__())
        global amqp_queue, nodefound_id
        amqp_queue.put(
            [method.routing_key, fit_common.json.loads(body)["nodeId"], body])
        nodefound_id = fit_common.json.loads(body)["nodeId"]

    def check_skupack(self):
        sku_installed = fit_common.rackhdapi('/api/2.0/skus')['json']
        if len(sku_installed) < 2:
            return False
        else:
            return True

    def _process_message(
            self,
            action,
            typeid,
            nodeid,
            messagetype,
            severity,
            amqp_message_body):
        expected_key = messagetype + "." + action + \
            "." + severity + "." + typeid + "." + nodeid
        expected_payload = {
            "type": messagetype,
            "action": action,
            "typeId": typeid,
            "nodeId": nodeid,
            "severity": severity,
            "version": "1.0",
            "createdAt": {}}
        self._compare_message(
            amqp_message_body,
            expected_key,
            expected_payload)

    def _compare_message(self, amqpmessage, expected_key, expected_payload):
        routing_key = amqpmessage[0]
        amqp_body = amqpmessage[2]
        self.assertEquals(
            routing_key,
            expected_key,
            "Routing key is not expected! expect {0}, get {1}" .format(
                expected_key,
                routing_key))
        try:
            amqp_body_json = fit_common.json.loads(amqp_body)
        except ValueError:
            logs.error("FAILURE - The message body is not json format!")
            return
        try:
            self.assertEquals(
                amqp_body_json['version'],
                expected_payload['version'],
                "version field not correct! expect {0}, get {1}" .format(
                    expected_payload['version'],
                    amqp_body_json['version']))
            self.assertEquals(
                amqp_body_json['typeId'], expected_payload['typeId'],
                "typeId field not correct!  expect {0}, get {1}"
                .format(expected_payload['typeId'], amqp_body_json['typeId']))
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
        except ValueError as e:
            self.fail(
                "FAILURE - expected key is missing in the AMQP message!{0}".format(e))

    def test_sel_alert(self):
        # The SEL log poller test will inject a CPU IERR event in the node BMC and moniter the AMQP message queue
        node_collection = test_api_utils.get_node_list_by_type("compute")
        nodeid = ""
        # Check is skupack is installed. If no skupack installed, we won't get any SEL alert
        skupack_installed = self.check_skupack()
        for dummy in node_collection:
            nodeid = node_collection[
                random.randint(
                    0, len(node_collection) - 1)]
            if fit_common.rackhdapi(
                '/api/2.0/nodes/' +
                    nodeid)['json']['name'] != "Management Server":
                break
        logs.debug_2('Checking OBM setting...')
        node_obm = fit_common.rackhdapi(
            '/api/2.0/nodes/' + nodeid)['json']['obms']
        if node_obm == []:
            self.assertTrue(
                self._apply_obmsetting_to_node(nodeid),
                "Fail to apply obm setting!")
        # Clear sel to avoid the sel log full
        test_api_utils.run_ipmi_command_to_node(nodeid, "sel clear")
        # Find the SEL poller id. This id will be used to validate AMQP message body.
        pollerid = self._get_ipmi_poller_by_node(nodeid, "selEntries")
        logs.debug('launch AMQP thread for sel alert')
        sel_worker = AmqpWorker(
            exchange_name="on.events",
            topic_routing_key="polleralert.sel.#." + nodeid,
            external_callback=self.amqp_callback,
            timeout=200)
        sel_worker.setDaemon(True)
        sel_worker.start()
        # Send out sel iERR injection.
        command = "raw 0x0a 0x44 0x01 0x00 0x02 0xab 0xcd 0xef 0x00 0x01 0x00 0x04 0x07 0x02 0xef 0x00 0x00 0x00"
        test_api_utils.run_ipmi_command_to_node(nodeid, command)
        if skupack_installed:
            self._wait_amqp_message(200)
            workflow_amqp = amqp_queue.get()
            self._process_message(
                "sel.updated",
                pollerid,
                nodeid,
                "polleralert",
                "critical",
                workflow_amqp)
            sel_worker.dispose()
        else:
            self.fail("No skupack is intalled in the RackHD. The SEL alert test will fail.")

    def test_chassis_power_updated(self):
        node_collection = test_api_utils.get_node_list_by_type("compute")
        nodeid = node_collection[
            random.randint(
                0, len(node_collection) - 1)]
        logs.debug_2('Checking OBM setting...')
        node_obm = fit_common.rackhdapi(
            '/api/2.0/nodes/' + nodeid)['json']['obms']
        if node_obm == []:
            self.assertTrue(
                self._apply_obmsetting_to_node(nodeid),
                "Fail to apply obm setting!")
        pollerid = self._get_ipmi_poller_by_node(nodeid, "chassis")
        logs.debug('launch AMQP thread for chassis state monitor')
        chassis_worker = AmqpWorker(
            exchange_name="on.events",
            topic_routing_key="polleralert.chassispower.updated.#",
            external_callback=self.amqp_callback,
            timeout=200)
        chassis_worker.setDaemon(True)
        chassis_worker.start()
        ssh_output = test_api_utils.run_ipmi_command_to_node(nodeid, "chassis power status")
        # If in initial state the chassis power is on, then the test will do power off->power on
        # Otherwise it will do power on -> power off
        if "Chassis Power is on" in ssh_output['stdout']:
            command1 = "chassis power off"
            command2 = "chassis power on"
        else:
            command1 = "chassis power on"
            command2 = "chassis power off"
        logs.debug('Power off/on node to change chassis power state')
        test_api_utils.run_ipmi_command_to_node(nodeid, command1)
        logs.debug('Wait chassis power update')
        self._wait_amqp_message(200)
        workflow_amqp = amqp_queue.get()
        self._process_message(
            "chassispower.updated",
            pollerid,
            nodeid,
            "polleralert",
            "information",
            workflow_amqp)
        # Power on node
        logs.debug('Wait chassis power update')
        test_api_utils.run_ipmi_command_to_node(nodeid, command2)
        logs.debug('Wait chassis power update')
        self._wait_amqp_message(200)
        workflow_amqp = amqp_queue.get()
        self._process_message(
            "chassispower.updated",
            pollerid,
            nodeid,
            "polleralert",
            "information",
            workflow_amqp)
        chassis_worker.dispose()


if __name__ == '__main__':
    unittest.main()
