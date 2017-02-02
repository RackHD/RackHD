from config.api2_0_config import *
from config.settings import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from proboscis.asserts import *
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads
from on_http_api2_0 import rest
import os
import subprocess
import json
import tarfile
import shutil
import requests
from config.amqp import *
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
import time

LOG = Log(__name__)

@test(groups=['sel_alert_poller_api2.tests'])
class SELPollerAlertTests(object):
    def __init__(self):
        self.__client = config.api_client
        self.__computeNodes = []
        self.__rootDir = "/tmp/tarball/"
        self.__skuPackTarball = self.__rootDir + "mytest.tar.gz"
        self.__rootDir = "/tmp/tarball/"
        self.__event_total = 1
        self.__event_count = 0
        self.__amqp_alert = {}
        self.__bmc_credentials = get_bmc_cred()
        self.__skupacknumber = 0
        self.__task = None
        self.delete_skus()# clear any skus

    @test(groups=['SEL_alert_poller_api2.tests', 'post_skupacks'])
    def post_skupacks(self):
        """Test posting skupacks that starts the sel alert poller"""
        #In order for the sel alert poller to be created there should be a
        #skupack posted  with the alerts in the config.json file
        #The code below dynamically creates the skupack  rule for each node based on their catalog

        Api().nodes_get_all()
        all_nodes = loads(self.__client.last_response.data)

        for n in all_nodes:
            if n.get('type') == 'compute':
                # get the catalog of the node
                node_id = n.get('id')
                Api().nodes_get_catalog_source_by_id(identifier=node_id, source='dmi')
                node_catalog_data = loads(self.__client.last_response.data)

                # get the node IP
                Api().nodes_get_catalog_source_by_id(identifier=node_id, source='bmc')
                node_bmc = loads(self.__client.last_response.data)
                node_ip = node_bmc['data']['IP Address']

                if len(node_catalog_data) > 0:

                    # Find the size of the SEL and how many entries can it handles
                    selInfoObj = self.selInfoObj(node_ip, "sel info")
                    free_bytes = int(selInfoObj['Free Space'][0])
                    available_sel_entries = free_bytes / 16
                    self.__computeNodes.append({"node_id":n.get('id'),"node_ip":node_ip,"available_sel_entries":available_sel_entries})

                    # dynamically update the skupack rule  with a value from the cataloged node
                    node_manufacturer = \
                        node_catalog_data.get('data').get("System Information").get("Manufacturer").split(" ")[0]

                    # Generate and post the skupack with the updated rule
                    self.generateTarball(node_manufacturer)
                    self.__file = {'file': open(self.__skuPackTarball, 'rb')}
                    URL = config.host + config.api_root + '/skus/pack'
                    LOG.info("URL {0}".format(URL))
                    requests.adapters.DEFAULT_RETRIES = 3
                    for n in range(0, 5):
                        try:
                            LOG.info("Number of attempt to post  the skupack :  {0}".format(n))
                            res = requests.post(URL, files=self.__file)
                            break
                        except requests.ConnectionError, e:
                            LOG.info("Request Error {0}: ".format(e))
                    assert_equal(201, res.status_code, message=res.reason)

    @test(groups=['SEL_alert_poller_api2.tests', 'check_pollers'],depends_on_groups=['post_skupacks'])
    def check_selEntries_poller(self):
        """Test: Checking that the selEntries pollers have started for all of the compute nodes"""

        for n in self.__computeNodes:
            found_poller = False
            Api().nodes_get_pollers_by_id(identifier=n['node_id'])
            pollers = loads(self.__client.last_response.data)
            for poller in pollers:
                if(poller['config']['command']== "selEntries"):
                    n['poller_id'] = poller['id']
                    found_poller =  True

            assert_equal(found_poller, True)

    @test(groups=['SEL_alert_poller_api2.tests', 'inject_single_error'],depends_on_groups=['check_pollers'])
    def test_single_entry(self):
        """Test A single alert"""
        #The raw command below create the follwing entry
             # SEL Record ID          : 6e8c
             # Record Type           : 02
             # Timestamp             : 01/01/1970 01:15:49
             # Generator ID          : 0001
             # EvM Revision          : 04
             # Sensor Type           : Processor
             # Sensor Number         : 02
             # Event Type            : Sensor-specific Discrete
             # Event Direction       : Deassertion Event
             # Event Data            : 000000
             # Description           : IERR

        for n in self.__computeNodes:

                # Inject a single SEL entry after clearing the sel
                self.run_ipmitool_command(n['node_ip'], "sel clear")
                self.verify_empty_sel(n['node_ip'])
                command = "raw 0x0a 0x44 0x01 0x00 0x02 0xab 0xcd 0xef 0x00 0x01 0x00 0x04 0x07 0x02 0xef 0x00 0x00 0x00"
                self.run_ipmitool_command(n['node_ip'], command)


                #listen to AMQP
                LOG.info('starting amqp listener for node {0}'.format(id))
                self.__task = WorkerThread(AMQPWorker(queue=QUEUE_SEL_ALERT,
                                    callbacks=[self.handle_sel_event]), 'singleAlert')
                self.__event_count = 0
                self.__event_total = 1

                def start(worker, id):
                    worker.start()
                tasks = WorkerTasks(tasks=[self.__task], func=start)

                tasks.run()
                tasks.wait_for_completion(timeout_sec=600)
                assert_false(self.__task.timeout, \
                        message='timeout waiting for task {0}'.format(self.__task.id))
                #In addition to the ipmitool readout, RackHD adds two elements
                # ("Sensor Type Code" & "Event Type Code") to the alert
                # validate that the sel raw read is being  decoded correctly
                assert_equal(self.__amqp_alert["data"]["alert"]['reading']["Description"],"IERR")
                assert_equal(self.__amqp_alert["data"]["alert"]['reading']["Event Type Code"], "6f")
                assert_equal(self.__amqp_alert["data"]["alert"]['reading']["Sensor Type Code"], "07")
                self.__amqp_alert = {}

    @test(groups=['SEL_alert_poller_api2.tests', 'sel_overflow_simulation'], depends_on_groups=['inject_single_error'])
    def test_sel_overflow(self):
        """Test: SEL overflow simulation """
        #This test validates that sel poller alert can handle a SEL with the overflow option turned on.
        #In this case when the sel is full the first sel entry in the log won't have record ID 1
        #This is could only be simulated on virtual node by issuing a clear command

        for n in self.__computeNodes:
            self.run_ipmitool_command(n['node_ip'], "sel clear")
            self.verify_empty_sel(n['node_ip'])
            command = "raw 0x0a 0x44 0x01 0x00 0x02 0xab 0xcd 0xef 0x00 0x01 0x00 0x04 0x07 0x02 0xef 0x00 0x00 0x00"
            self.run_ipmitool_command(n['node_ip'], command)
            selInfoObj = self.selInfoObj(n['node_ip'], "sel get 0")
            initial_first_SEL_entry = int(selInfoObj["SEL Record ID"][0],16)
            LOG.info(selInfoObj["SEL Record ID"][0])

            self.run_ipmitool_command(n['node_ip'], "sel clear")
            self.verify_empty_sel(n['node_ip'])
            command = "raw 0x0a 0x44 0x01 0x00 0x02 0xab 0xcd 0xef 0x00 0x01 0x00 0x04 0x07 0x02 0xef 0x00 0x00 0x00"
            self.run_ipmitool_command(n['node_ip'], command)
            selInfoObj = self.selInfoObj(n['node_ip'], "sel get 0")
            LOG.info(selInfoObj["SEL Record ID"][0])
            new_first_SEL_entry = int(selInfoObj["SEL Record ID"][0],16)

            if(new_first_SEL_entry != 0):
                LOG.info("Succesfully simulated the SEL overflow behavior")
            else:
                LOG.info("Couldn't simulate the SEL overflow behavior")

            assert_equal(new_first_SEL_entry,initial_first_SEL_entry + 1)

    @test(groups=['SEL_alert_poller_api2.tests', 'inject_full_sel'],depends_on_groups=['inject_single_error'])
    def test_full_sel(self):
        """Test: Full sel log"""
        #Validate the poller can digest data from a full sel log all at once

        for n in self.__computeNodes:
            # listen to AMQP
            LOG.info('starting amqp listener for node {0}'.format(id))
            self.__task = WorkerThread(AMQPWorker(queue=QUEUE_SEL_ALERT,
                                            callbacks=[self.handle_sel_event]), 'fullSel')
            self.run_ipmitool_command(n['node_ip'], "sel clear")
            self.verify_empty_sel(n['node_ip'])

            self.create_selEntries_file(n["available_sel_entries"])
            self.__amqp_alert = {}
            self.run_ipmitool_command((n['node_ip']), "sel add /tmp/selError.txt")
            #time.sleep(1)
            self.__event_count = 0
            self.__event_total = n["available_sel_entries"]

            def start(worker, id):
                worker.start()
            tasks = WorkerTasks(tasks=[self.__task], func=start)
            tasks.run()
            tasks.wait_for_completion(timeout_sec=600)
            assert_false(self.__task.timeout, \
                    message='timeout waiting for task {0}'.format(self.__task.id))
            assert_equal(self.__event_count, n["available_sel_entries"])

    def run_ipmitool_command(self, ip ,command):
        ipmitool_command = "ipmitool -I lanplus -H " + ip +" -U " + self.__bmc_credentials[0] +" -P " + self.__bmc_credentials[1] + " " + command
        f = os.popen( ipmitool_command)
        ipmi_return = f.read()
        LOG.info("ipmi ipmitool_command: {0}".format(ipmitool_command))
        return ipmi_return

    def verify_empty_sel(self,ip,entries=None):
        #recursive function that check that the SEL has been cleared
        #This is function is  more efficient than using a sleep/wait method
        #especially when running on actual hardware
        if entries > 1 or entries == None :
            selInfoObj = self.selInfoObj(ip, "sel info")
            entries = int(selInfoObj['Entries'][0])
            time.sleep(0.5)
            self.verify_empty_sel(ip,entries)
        else:
            return

    def handle_sel_event(self,body,message):
        routeId = message.delivery_info.get('routing_key').split('polleralert.sel.updated')[1]
        assert_not_equal(routeId,None)
        message.ack()
        self.__amqp_alert = body
        self.__event_count = self.__event_count + 1

        if self.__event_count == self.__event_total:
            self.__task.worker.stop()
            self.__task.running = False

    def generateTarball(self, ruleUpdate=None):
        #This function genetare a skupack tarball with a cutome rule

        if os.path.isdir(self.__rootDir):
            shutil.rmtree(self.__rootDir)
        os.mkdir(self.__rootDir)
        tarballDirs = ["profiles", "static", "tasks", "templates", "workflows"]
        for dir in tarballDirs:
            os.mkdir(self.__rootDir + dir)
        self.__skupacknumber = self.__skupacknumber +1
        name ="skupack_"+ str(self.__skupacknumber)
        self.__config_json = {
            "name": name,
            "rules": [
                {
                    "path": "dmi.System Information.Manufacturer",
                    "contains": "Quanta"
                }
            ],
            "skuConfig": {
                "value1": {
                    "value": "value"
                },
                "sel": {
                    "alerts": [
                        {
                            "Event Type Code": "01",
                            "Description": "/.+Non-critical going.+/",
                            "action": "warning"
                        },
                        {
                            "Event Type Code": "01",
                            "Description": "/(.+Critical going.+)|(Lower Non-recoverable going low)|(Upper Non-recoverable going high)/",
                            "action": "critical"
                        },
                        {
                            "Sensor Type Code": "07",
                            "Event Type Code": "6f",
                            "Event Data": "/050000|080000|0a0000/",
                            "action": "warning"
                        },
                        {
                            "Sensor Type Code": "07",
                            "Event Type Code": "6f",
                            "Event Data": "/000000|010000|020000|030000|040000|060000|0b0000/",
                            "action": "critical"
                        },
                        {
                            "Event Data": "00ffff",
                            "action": "warning"
                        },
                        {
                            "Sensor Type": "Event Logging Disabled",
                            "Description": "Log full",
                            "Event Direction": "Assertion Event",
                            "action": "warning"
                        }
                    ]
                }
            },
            "workflowRoot": "workflows",
            "taskRoot": "tasks",
            "httpProfileRoot": "profiles",
            "httpTemplateRoot": "templates",
            "httpStaticRoot": "static"
        }
        if (ruleUpdate != None):
            self.__config_json['rules'][0]['contains'] = ruleUpdate

        with open(self.__rootDir + 'config.json', 'w') as f:
            json.dump(self.__config_json, f)
        f.close()

        os.chdir(self.__rootDir)
        with tarfile.open(self.__rootDir + "mytest.tar.gz", mode="w:gz") as f:
            for name in ["config.json", "profiles", "static", "tasks", "templates", "workflows"]:
                f.add(name)

    def delete_skus(self):
        #delete all the skus before post new skus with the right rule that match the nodes
        Api().skus_get()
        rsp = self.__client.last_response
        data = loads(self.__client.last_response.data)
        for item in data:
            Api().skus_id_delete(item.get("id"))

    def create_selEntries_file(self, numberOfEntries):
        #This function create a file of sel entries in order to be writen into the SEl
        entries = "0x04 0x09 0x01 0x6f 0x00 0xff 0xff # Power Unit #0x01 Power off/down"
        singleEntry = "0x04 0x09 0x01 0x6f 0x00 0xff 0xff # Power Unit #0x01 Power off/down"

        for index in range(numberOfEntries-1):
            entries = entries + '\n' + singleEntry

        with open('/tmp/selError.txt', 'w') as f:
            f.write(entries)
        f.close()

    def selInfoObj(self,node_ip, command):
        #return the sel info in a dictionary format
        selInfoUnprocessed = self.run_ipmitool_command(node_ip, command)
        selInfoArray = selInfoUnprocessed.split('\n')
        selInfoObj = {}
        for entry in selInfoArray:
            keyVal = entry.split(':')
            keyVal[0] = keyVal[0].rstrip()
            if (entry.find(':') != -1):
                keyVal[1] = keyVal[1].strip().split()
                selInfoObj[keyVal[0]] = keyVal[1]
            else:
                selInfoObj[keyVal[0]] = None
        return selInfoObj
