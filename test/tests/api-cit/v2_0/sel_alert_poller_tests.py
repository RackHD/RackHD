'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging
import tarfile
import shutil
import requests
import time
import os

from sm_plugin import smp_get_stream_monitor

from config.api2_0_config import config
from config.settings import get_bmc_cred
from on_http_api2_0 import ApiApi as Api
from json import dump, dumps, loads
from api_utils import get_by_string
from on_http_api2_0.rest import ApiException

from nose.plugins.attrib import attr
from nosedep import depends

logs = flogging.get_loggers()

SKU_ATTACH_WAIT_TIME = 15
TEST_SKU_PACK_NAME = 'SKUPACK_SEL_POLLER_TEST'


@attr(regression=False, smoke=True, workflows_tasks_api2_tests=True)
class SELPollerAlertTests(fit_common.unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        # Get the stream-monitor plugin for AMQP
        cls._amqp_sp = smp_get_stream_monitor('amqp')

        if cls._amqp_sp and cls._amqp_sp.has_amqp_server:
            # Create the "all events" tracker
            cls._on_events_tracker = cls._amqp_sp.create_tracker('on-events-all', 'on.events', 'polleralert.#')
        else:
            cls._on_events_tracker = None

        # We have context information that needs to be passed from test-to-test. Set up the template
        # space.
        cls._run_context = {
            'node_id': None,
            'bmc_ip': None,
            'sku_id': None,
            'original_sku_id': None,
            'available_sel_entries': None,
            'sku_pack_number': None,
            'poller_id': None,
            'bmc_creds': get_bmc_cred()
        }
        cls.__rootDir = "/tmp/tarball/"
        cls.__skuPackTarball = cls.__rootDir + "mytest.tar.gz"

    @classmethod
    def tearDownClass(cls):
        if cls._on_events_tracker:
            # remove created sku pack (it may miss on various test failures, so ignore errors)
            try:
                Api().skus_id_delete(cls._run_context['sku_id'])

            except ApiException:
                pass

            # Clearing out the full sel logs after test script runs
            ip = cls._run_context['bmc_ip']
            bmc_creds = cls._run_context['bmc_creds']
            ipmitool_command = "ipmitool -I lanplus -H {0} -U {1} -P {2} {3}".format(
                ip, bmc_creds[0], bmc_creds[1], "sel clear")
            ipmi_rsp_data = fit_common.remote_shell(ipmitool_command)
            if ipmi_rsp_data['exitcode'] != 0:
                logs.info(" Warning: could not clear sel logs from node %s on script clean up", cls._run_context['node_id'])

    def setUp(self):
        if not self._on_events_tracker:
            raise fit_common.unittest.SkipTest('Skipping AMQP test because no AMQP server defined')

        # attach a processor to the on-events-tracker amqp tracker. Then we can
        # attach indiviual match-clauses to this in each test-case.
        self.__qproc = self._amqp_sp.get_tracker_queue_processor(self._on_events_tracker, start_at='now')

    def __get_result(self):
        return self.__client.last_response

    def __get_data(self):
        return loads(self.__get_result().data)

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

    def __build_info_vblock(self, message_type, action, typeid, nodeid, data=None):
        expected_payload = {
            "type": message_type,
            "action": action,
            "typeId": typeid,
            "nodeId": nodeid,
            "severity": "critical",
            "createdAt": "<<present>>",
            "data": "<<present>>",
            "version": "1.0"
        }

        # add possible data area
        if data:
            expected_payload['data'] = data

        expected_rk = "{}.{}.critical.{}.{}".format(message_type, action, typeid, nodeid)

        ex = {
            'body': expected_payload,
            'routing_key': expected_rk
        }
        return ex

    def test_post_skupacks(self):
        # """Test posting skupacks that starts the sel alert poller"""
        # In order for the sel alert poller to be created there should be a
        # skupack posted  with the alerts in the config.json file
        # The code below dynamically creates the skupack  rule for each node based on their catalog

        Api().nodes_get_all()
        all_nodes = self.__get_data()

        # get the catalog of the node
        node_id, original_sku_id = self.__find_node_with_sku(all_nodes)
        self.assertIsNotNone(node_id, 'No node with with SKU and OBMs found')
        logs.info("node Id: %s  original sku id: %s", node_id, original_sku_id)

        # get the node BMC IP address
        Api().nodes_get_catalog_source_by_id(identifier=node_id, source='bmc')
        node_bmc = self.__get_data()
        node_bmc_mac = get_by_string(node_bmc, 'data.MAC Address')
        logs.info("bmc MAC address: %s", node_bmc_mac)

        Api().lookups_get(q=node_bmc_mac)
        dhcp_entry = self.__get_data()
        bmc_ip = dhcp_entry[0].get('ipAddress')
        logs.info("SLE object: %s", bmc_ip)

        self.__run_ipmitool_command(bmc_ip, "sel clear")

        Api().nodes_get_catalog_source_by_id(identifier=node_id, source='dmi')
        node_dmi_catalog = self.__get_data()

        if len(node_dmi_catalog) > 0:

            # Find the size of the SEL and how many entries can it handles
            available_sel_entries = self.__get_available_sel_entries(bmc_ip)

            # Deleting the sku pack
            self.__delete_skus(sku_name=TEST_SKU_PACK_NAME)

            # Generate and post the skupack with the updated rule
            self.__generate_tar_ball(node_dmi_catalog, original_sku_id)
            self.__file = {'file': open(self.__skuPackTarball, 'rb')}
            URL = config.host + config.api_root + '/skus/pack'
            logs.info("URL {0}".format(URL))
            requests.adapters.DEFAULT_RETRIES = 3
            sku_id = None
            for n in range(0, 5):
                try:
                    logs.info("Number of attempt to post  the skupack :  {0}".format(n))
                    res = requests.post(URL, files=self.__file)
                    sku_id = loads(res.text).get('id')
                    break
                except requests.ConnectionError as e:
                    logs.info("Request Error {0}: ".format(e))

            self.assertIsNotNone(res, msg='Connection could not be established')
            self.assertEqual(201, res.status_code, msg=res.reason)
            self.assertIsNotNone(sku_id, msg='Sku ID not found')

            # Wait fot the POSTed sku to attach
            self.__wait_for_sku_to_attach(node_id, sku_id)

            self.__set_run_context("node_id", node_id)
            self.__set_run_context("bmc_ip", bmc_ip)
            self.__set_run_context("sku_id", sku_id)
            self.__set_run_context("original_sku_id", original_sku_id)
            self.__set_run_context("available_sel_entries", available_sel_entries)
        else:
            logs.warning('selInfoDuct we have none in a row!!!')

    @depends(after='test_post_skupacks')
    def test_check_selEntries_poller(self):
        # """Test: Checking that the selEntries pollers have started for all of the compute nodes"""
        node_id = self.__get_run_context('node_id')

        Api().nodes_get_pollers_by_id(identifier=node_id)
        pollers = self.__get_data()
        for poller in pollers:
            if get_by_string(poller, 'config.command') == "selEntries":
                self.__set_run_context('poller_id', poller['id'])
                break
        self.assertIsNotNone(self.__get_run_context('poller_id'),
                             msg='SelEntries poller not found for node {}'.format(node_id))

    @depends(after='test_check_selEntries_poller')
    def test_single_entry(self):
        # """Test A single alert"""
        # The raw command below create the following entry
        #       SEL Record ID         : 6e8c
        #       Record Type           : 02
        #       Timestamp             : 01/01/1970 01:15:49
        #       Generator ID          : 0001
        #       EvM Revision          : 04
        #       Sensor Type           : Processor
        #       Sensor Number         : 02
        #       Event Type            : Sensor-specific Discrete
        #       Event Direction       : Deassertion Event
        #       Event Data            : 000000
        #       Description           : IERR
        bmc_ip = self.__get_run_context('bmc_ip')
        node_id = self.__get_run_context('node_id')
        poller_id = self.__get_run_context('poller_id')

        # data = {'alert': {
        #     'reading': {
        #         'Description': 'IERR',
        #         'Event Type Code': '6f',
        #         'Sensor Type Code': '07'
        #     }
        # }}

        self.__qproc.match_on_routekey('polleralert-sel-update',
                                       routing_key='polleralert.sel.updated.#.{}.{}'.format(poller_id,
                                                                                            node_id),
                                       validation_block=self.__build_info_vblock('polleralert',
                                                                                 'sel.updated',
                                                                                 poller_id,
                                                                                 node_id))

        # Inject a single SEL entry after clearing the sel
        self.__run_ipmitool_command(bmc_ip, "sel clear")
        self.__verify_empty_sel(bmc_ip)

        command = "raw 0x0a 0x44 0x01 0x00 0x02 0xab 0xcd 0xef 0x00 0x01 0x00 0x04 0x07 0x02 0xef 0x00 0x00 0x00"
        self.__run_ipmitool_command(bmc_ip, command)

        # wait for the results
        results = self._amqp_sp.finish(timeout=180)
        results[0].assert_errors(self)

    @depends(after='test_single_entry')
    def test_full_sel(self):
        # """Test: Full sel log"""
        # listen to AMQP

        bmc_ip = self.__get_run_context('bmc_ip')
        node_id = self.__get_run_context('node_id')
        poller_id = self.__get_run_context('poller_id')
        available_sel_entries = self.__get_run_context('available_sel_entries')

        self.__qproc.match_on_routekey('polleralert-sel-update',
                                       min=available_sel_entries - 3, max=available_sel_entries,
                                       routing_key='polleralert.sel.updated.#.{}.{}'.format(poller_id, node_id))

        self.__run_ipmitool_command(bmc_ip, "sel clear")
        self.__verify_empty_sel(bmc_ip)

        sel_file = self.__create_selEntries_file(available_sel_entries)
        fit_common.remote_shell('ls')
        fit_common.scp_file_to_host(sel_file)

        self.__run_ipmitool_command(bmc_ip, "sel add ~/selError.txt")

        # wait for the results
        results = self._amqp_sp.finish(timeout=360)
        results[0].assert_errors(self)

    def __run_ipmitool_command(self, ip, command):
        bmc_creds = self.__get_run_context('bmc_creds')
        ipmitool_command = "ipmitool -I lanplus -H {0} -U {1} -P {2} {3}".format(
            ip, bmc_creds[0], bmc_creds[1], command)

        ipmi_rsp_data = fit_common.remote_shell(ipmitool_command)
        # logs.info('ipmi_rsp_data: %s', dumps(ipmi_rsp_data, indent=4))
        if ipmi_rsp_data['exitcode'] != 0:
            if 'Add SEL Entry failed: Out of space' not in ipmi_rsp_data['stdout']:
                self.assertEqual(ipmi_rsp_data['exitcode'], 0,
                                 'ipmitool command fail. exit code: %s',
                                 ipmi_rsp_data['exitcode'])

        ipmi_cmd_data = ipmi_rsp_data['stdout']

        logs.info("ipmi ipmitool_command: {0}".format(ipmi_cmd_data))
        return ipmi_cmd_data

    def __verify_empty_sel(self, ip, entries=None):
        time_to_wait = 10 - 1

        while entries > 1:
            selInfoObj = self.__get_SelInfo(ip, "sel info")
            entries = int(selInfoObj['Entries'][0])
            time_to_wait -= 1
            if time_to_wait < 0:
                return False
            time.sleep(1)
        return True

    def __generate_tar_ball(self, node_dmi_catalog, original_sku_id):
        # This function genetare a skupack tarball with a cutome rule

        if os.path.isdir(self.__rootDir):
            shutil.rmtree(self.__rootDir)
        os.mkdir(self.__rootDir)
        tarballDirs = ["profiles", "static", "tasks", "templates", "workflows"]
        for dir in tarballDirs:
            os.mkdir(self.__rootDir + dir)
        name = TEST_SKU_PACK_NAME
        self.__config_json = {
            "name": name,
            "rules": [
                {
                    "path": "dmi.Base Board Information.Serial Number",
                    "contains": " "
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
                            "Description": "/(.+Critical going.+)|(Lower Non-recoverable going low)" +
                                           "|(Upper Non-recoverable going high)/",
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
                            "Sensor Type Code": "14",
                            "Event Type Code": "6f",
                            "Event Data": "/000000|020000|010000|030000|040000/",
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

        # fill in mock sku using the provided node_dmi_catalog
        node_serial_number = get_by_string(node_dmi_catalog, 'data.Base Board Information.Serial Number').split(" ")[0]
        logs.info('Node serial number is: %s', node_serial_number)
        self.__config_json['rules'][0]['contains'] = node_serial_number

        # if there is no sku associated with this node, skip copy
        if original_sku_id:
            # copy the rules from the original sku into the mock sku
            Api().skus_id_get(identifier=original_sku_id)
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)
            self.assertEqual(200, result.status, msg=result.reason)
            rules = get_by_string(data, 'rules')
            self.__config_json['rules'].extend(rules)
            logs.info("Sku rules are: \n%s\n", dumps(self.__config_json['rules'], indent=4))

        with open(self.__rootDir + 'config.json', 'w') as f:
            dump(self.__config_json, f)
        f.close()

        os.chdir(self.__rootDir)
        with tarfile.open(self.__rootDir + "mytest.tar.gz", mode="w:gz") as f:
            for name in ["config.json", "profiles", "static", "tasks", "templates", "workflows"]:
                f.add(name)

    def __delete_skus(self, sku_id=None, sku_name=None):
        if sku_id and sku_name:
            return False

        if sku_name:
            sku_id = self.__get_sku_id_from_name(sku_name)
            if not sku_id:
                return

        if not sku_id:
            sku_id = self.__class__.__computeNode.get('sku_id')

        # remove created sku pack
        try:
            Api().skus_id_delete(sku_id)
            rsp = self.__client.last_response
            self.assertEqual(204, rsp.status, msg=rsp.reason)

        except ApiException as e:
            self.assertEqual(404, e.status,
                             msg="status = {1}, sku id {0} was not expected"
                             .format(sku_id, e.status))
        return True

    def __create_selEntries_file(self, numberOfEntries, singleEntry=None, filePath='/tmp/selError.txt'):
        # This function create a file of sel entries in order to be writen into the SEl
        entries = ''

        if not singleEntry:
            singleEntry = "0x04 0x14 0x00 0x6F 0x00 0x00 0x00 # Button # (W) Power Button pressed"
            # singleEntry = "0x04 0x09 0x01 0x6f 0x00 0xff 0xff # Power Unit #0x01 Power off/down"

        for index in range(numberOfEntries):
            if entries:
                entries += '\n'
            entries += singleEntry

        with open(filePath, 'w') as f:
            f.write(entries)
        f.close()
        return filePath

    def __get_SelInfo(self, bmc_ip, command):
        # return the sel info in a dictionary format
        selInfoUnprocessed = self.__run_ipmitool_command(bmc_ip, command)
        logs.info(' !!!! raw sel info: %s', selInfoUnprocessed)
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
        logs.info('sel info: %s', dumps(selInfoObj, indent=4))
        return selInfoObj

    def __find_node_with_sku(self, node_list):
        '''
            Find a compute node with an assocaited sku attached
            If no node is found with an attached sku, None is
            returned as the node id.

            :param node_list: list of nodes
            :return node_id, sku_id
        '''
        if node_list:
            for node in node_list:
                if node.get('type') == 'compute' and node.get('sku') and node.get('obms'):
                    # update the sku rule above (rules[0].name.contains) with a value from the cataloged node
                    sku_id = node.get('sku').split("/")[4]
                    logs.info("sku id: %s", sku_id)
                    Api().skus_id_get(identifier=sku_id)
                    sku = loads(self.__client.last_response.data)
                    if "Unidentified-Compute" in sku.get('name'):
                        continue

                    logs.info("Node id %s", node.get('id'))
                    logs.info("Original node sku id %s", sku_id)
                    logs.debug("SKU dump: \n%s\n", dumps(sku, indent=4))

                    return node.get('id'), sku_id

        return None, None

    def __wait_for_sku_to_attach(self, node_id, sku_id):
        '''
            Wait for the provided sku to attach the the provides node
            Note: Attachment timeout or request error will cause an assert.

            :param node_id: Id of node in which the sku is to attach
            :param sku_id: Id of sku this is to attach
            :return None
        '''
        # Give enough time to wait the sku discovery finishes
        time.sleep(3)
        retries = SKU_ATTACH_WAIT_TIME
        while retries > 0:
            Api().nodes_get_by_id(identifier=node_id)
            result = self.__get_result()
            self.assertEqual(200, result.status, msg=result.reason)

            updated_node = self.__get_data()
            logs.info("node: %s", dumps(updated_node, indent=4))
            if updated_node['sku'] and sku_id == updated_node['sku'].split("/")[4]:
                logs.info("SKU id %s is now attached to node %s:", sku_id, node_id)
                break

            retries -= 1
            self.assertNotEqual(retries, 0, msg="Node {0} never assigned with the new sku {1}".format(node_id, sku_id))
            time.sleep(1)

    def __get_sku_id_from_name(self, name):
        Api().skus_get()
        skus = self.__get_data()
        for n in skus:
            sku_name = n.get('name')
            logs.info_6('Checking sku name %s', sku_name)
            self.assertIsNotNone(sku_name)
            if sku_name == name:
                return n.get('id')
        return None

    def __get_available_sel_entries(self, bmc_ip):
        # Find the size of the SEL and how many entries can it handles
        selInfoDict = self.__get_SelInfo(bmc_ip, "sel info")
        logs.warning("selInfoDuct=%s", selInfoDict)

        try:
            available_sel_entries = int(selInfoDict.get('# Free Units')[0])
        except:
            # default unit size for infraSim nodes
            unit_size = 16
            if 'Alloc Unit Size' in selInfoDict:
                unit_size = int(selInfoDict.get('Alloc Unit Size')[0])
            free_bytes = int(selInfoDict['Free Space'][0])
            available_sel_entries = free_bytes / unit_size
        return available_sel_entries
