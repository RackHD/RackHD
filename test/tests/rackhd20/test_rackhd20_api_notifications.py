'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.
Author(s):

This file tests the redfish alert feature in RackHD.
RacKHD is enabled to received redfish alerts from compute nodes on
the following route: /"API/2.0/notifications/alerts".
The test here simulates a node sending a redfish alert by posting
to RackHD on "/API/2.0/notifications/alerts".
Once RackHD receives the alert, it adds some context to it (node ID, SN, etc...)
and publishes into AMQP, the test check for the message on AMQP as well.
'''

from time import sleep
import Queue
import flogging
import logging
import pika
import unittest
import threading
import fit_common
from nose.plugins.attrib import attr
logs = flogging.get_loggers()
amqp_queue = Queue.Queue(maxsize=0)
from pymongo import MongoClient
from bson.objectid import ObjectId
import json

# Check the running test environment
if fit_common.fitargs()['stack'] in ['vagrant_guest', 'vagrant', 'vagrant_ucs']:
    env_vagrant = True
else:
    env_vagrant = False
AMQP_PORT = fit_common.fitports()['amqp_ssl']
MONGO_PORT = fit_common.fitports()['mongo_port']
HTTP_PORT = fit_common.fitports()['http']


class AmqpWorker(threading.Thread):
    def __init__(self, exchange_name, topic_routing_key, external_callback, timeout=10):
        threading.Thread.__init__(self)
        pika_logger = logging.getLogger('pika')
        if fit_common.VERBOSITY >= 8:
            pika_logger.setLevel(logging.DEBUG)
        elif fit_common.VERBOSITY >= 4:
            pika_logger.setLevel(logging.WARNING)
        else:
            pika_logger.setLevel(logging.ERROR)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=fit_common.fitargs()["rackhd_host"],
                                                                            port=AMQP_PORT))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=topic_routing_key)
        self.channel.basic_consume(external_callback, queue=queue_name)
        self.connection.add_timeout(timeout, self.dispose)

    def dispose(self):
        logs.debug_3('Pika connection timeout')
        if self.connection.is_closed is False:
            self.channel.stop_consuming()
            logs.debug_1("Attempting to close the Pika connection")
            self.thread_stop = True

    def run(self):
        logs.debug_7('start consuming')
        self.channel.start_consuming()


@attr(all=True, regression=False, smoke=True)
class test_alert_notification(unittest.TestCase):
    CLIENT = None
    CATALOGS_COUNT = None
    NODES_COUNT = None
    OBMS_COUNT = None

    @classmethod
    def setUpClass(self):
        if fit_common.fitargs()['stack'] == 'vagrant_guest':
            IP = "127.0.0.1"
        elif fit_common.fitargs()['stack'] in ['vagrant', 'vagrant_ucs']:
            IP = "10.0.2.2"
        else:
            logs.info(" Not running in a vagrant environment, skipping tests")
            return
        logs.debug_1("MONGO_PORT: {0}, AMQP_PORT: {1}, HTTP_PORT:{2}".format(MONGO_PORT, AMQP_PORT, HTTP_PORT))
        self.CLIENT = MongoClient('localhost', MONGO_PORT)
        self.db = self.CLIENT.pxe
        self.node = {
            "identifiers": ["FF:FF:FF:FF:FF:FF"],
            "name": "FF:FF:FF:FF:FF:FF",
            "relations": [],
            "tags": [],
            "type": "compute"
        }
        self.CLIENT = MongoClient('localhost', MONGO_PORT)
        self.db = self.CLIENT.pxe
        self.node = {
            "identifiers": ["FF:FF:FF:FF:FF:FF"],
            "name": "FF:FF:FF:FF:FF:FF",
            "relations": [],
            "tags": [],
            "type": "compute"
        }
        self.NODES_COUNT = self.db.nodes.count()
        self.OBMS_COUNT = self.db.obms.count()
        self.CATALOGS_COUNT = self.db.catalogs.count()
        logs.debug_3("Counts at first: Node {0}  Catalogs {1}  Obms {2}"
                     .format(self.NODES_COUNT, self.CATALOGS_COUNT, self.OBMS_COUNT))
        logs.debug_3('Number of nodes before the test = {0}'.format(self.NODES_COUNT))
        logs.debug_3('Number of obms before the test = {0}'.format(self.OBMS_COUNT))
        logs.debug_3('Number of catalogs before the test = {0}'.format(self.CATALOGS_COUNT))
        self.nodeID = self.db.nodes.insert(self.node)
        self.obm = {
            "config": {
                "host": IP,
                "user": "root",
                "password": "L3q4teHQz+nve6LfchHmow==.18jDStd2JuqpsVgQA/o81Q=="
            },
            "node": ObjectId(self.nodeID),
            "service": "ipmi-obm-service"
        }
        self.bmcCatalog = {
            "node": ObjectId(self.nodeID),
            "source": "bmc",
            "data": {
                "Set in Progress": "Set Complete",
                "Auth Type Support": "MD5",
                "Auth Type Enable": {
                    "Callback": "MD5 ",
                    "User": "MD5 ",
                    "Operator": "MD5 ",
                    "Admin": "MD5 ",
                    "OEM": ""
                },
                "IP Address Source": "DHCP Address",
                "IP Address": IP,
                "Subnet Mask": "255.255.255.0",
                "MAC Address": "64:00:6a:c3:52:32"
            }
        }
        self.ipmifruCatalog = {
            "node": ObjectId(self.nodeID),
            "source": "ipmi-fru",
            "data": {
                "Builtin FRU Device (ID 0)":
                    {
                        "Board Product": None,
                        "Product Serial": None,
                        "Board Serial": None
                    }
            }
        }
        self.payload = {
            "Context": "context string",
            "EventId": "8689",
            "EventTimestamp": "2017-04-05T10:31:29-0500",
            "EventType": "Alert",
            "MemberId": "7e675c8e-127a-11e7-9fc8-64006ac35232",
            "Message": "The coin cell battery in CMC 1 is not working.",
            "MessageArgs": ["1"],
            "MessageArgs@odata.count": 1,
            "MessageId": "CMC8572",
            "Severity": "critical"
        }

        cursor = self.db.nodes.find()
        for document in cursor:
            logs.info("Node collection:  {0}".format(document))

        cursor = self.db.obms.find({})
        for document in cursor:
            logs.debug_3("OBM collection: {0}".format(document))

        cursor = self.db.catalogs.find({})
        for document in cursor:
            logs.debug_3("Catalogs collection: : {0}".format(document))

    @classmethod
    def tearDownClass(self):
        global NODES_COUNT, CATALOGS_COUNT, OBMS_COUNT
        global env_vagrant

        # Skip the tear down if not in vagrant environment
        if env_vagrant is False:
            return

        logs.debug_3('finished redfish alert')
        self.db.obms.remove({"node": self.nodeID})
        self.db.catalogs.remove({"node": self.nodeID})
        self.db.nodes.remove({"_id": self.nodeID})

        nodesRemaining = self.db.nodes.count()
        obmsRemaining = self.db.obms.count()
        catalogsRemaining = self.db.catalogs.count()

        logs.debug_3('Number of nodes after the test = {0}'.format(nodesRemaining))
        logs.debug_3('Number of obms after the test = {0}'.format(obmsRemaining))
        logs.debug_3('Number of catalogs after the test = {0}'.format(catalogsRemaining))

        logs.debug_3(
            "Counts at the end: Node {0}  Catalogs {1}  Obms {2}"
            .format(self.NODES_COUNT, self.CATALOGS_COUNT, self.OBMS_COUNT))

        if (self.NODES_COUNT != nodesRemaining or
                self.CATALOGS_COUNT != catalogsRemaining or self.OBMS_COUNT != obmsRemaining):
            raise Exception("Couldn't restore the dataBase")

        cursor = self.db.nodes.find()
        for document in cursor:
            logs.info("Node collection:  {0}".format(document))

        cursor = self.db.obms.find()
        for document in cursor:
            logs.debug_3("OBM collection: {0}".format(document))

        cursor = self.db.catalogs.find()
        for document in cursor:
            logs.debug_3("Catalogs collection: : {0}".format(document))

    def _wait_amqp_message(self, timeout):
        global amqp_queue
        timecount = 0
        logs.debug_1("inQ wait number:{0},q:{1}".format(timecount, amqp_queue.empty()))
        while amqp_queue.empty() is True and timecount < timeout:
            logs.debug_1("Waiting for a message, run:{0},Q_Empty:{1}".format(timecount, amqp_queue.empty()))
            sleep(1)
            timecount = timecount + 1
        self.assertNotEquals(timecount, timeout, "AMQP message receive timeout")

    def amqp_callback(self, ch, method, properties, body):
        logs.data_log.debug_3(body.__str__())
        logs.data_log.debug_3("Executing the amqp Callback")
        global amqp_queue, nodefound_id
        amqp_queue.put(
            [method.routing_key, fit_common.json.loads(body)])

    def updateDb(self):
        obmCollection = self.db.obms
        obmID = obmCollection.insert(self.obm)
        bmcCatalogID = self.db.catalogs.insert(self.__class__.bmcCatalog)
        logs.debug_1("Added node: {0}".format(obmCollection.find_one({"node": self.nodeID})))
        logs.debug_1("ID of the added OBM: {0}".format(obmID))
        logs.debug_1("ID of the added BMC Catalog: {0}".format(bmcCatalogID))

    def validate(self, q):
        RoutingKey = q[0]
        receivedMsg = q[1]
        expectedMsg = self.payload
        expectedMsg["macAddress"] = "64:00:6a:c3:52:32",
        expectedMsg["ChassisName"] = self.ipmifruCatalog["data"]["Builtin FRU Device (ID 0)"]["Product Serial"],
        expectedMsg["serviceTag"] = self.ipmifruCatalog["data"]["Builtin FRU Device (ID 0)"]["Board Product"],
        expectedMsg["SN"] = self.ipmifruCatalog["data"]["Builtin FRU Device (ID 0)"]["Board Serial"]
        expectedMsg["originOfConditionPartNumber"] = None
        expectedMsg["originOfConditionSerialNumber"] = None
        logs.debug_1("Routing Key  {0}".format(RoutingKey))
        logs.debug_1("Received AMQP message: {0}".format(type(receivedMsg)))
        self.assertNotEquals(json.dumps(receivedMsg["data"]), json.dumps(expectedMsg), "unexpected AMQP message ")

    @unittest.skipUnless(env_vagrant is True, "Tests limited to running in vagrant test beds.")
    def test_post_alert_withIP(self):
        self.updateDb()
        sel_worker = AmqpWorker(
            exchange_name="on.events", topic_routing_key="node.alerts.#",
            external_callback=self.amqp_callback, timeout=100)
        sel_worker.setDaemon(True)
        sel_worker.start()

        for z in range(2):
            url = "http://{0}:{1}/api/2.0/notification/alerts".format(fit_common.fitargs()["rackhd_host"], HTTP_PORT)
            fit_common.restful(url, rest_action='post', rest_payload=self.payload)
            sleep(1)
            logs.debug_1("Post attempt {0}".format(z))

        logs.debug_1("Wait for the alert on the amqp bus")
        self._wait_amqp_message(100)
        amqp_message = amqp_queue.get()

        logs.debug_1("Dispose the Pika connection")
        sel_worker.dispose()

        logs.debug_1("Validate the content of the amqp msg")
        self.validate(amqp_message)
        logs.debug_1("Done with the alert test")


if __name__ == '__main__':
    unittest.main()
