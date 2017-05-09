"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import fit_path  # NOQA: unused import
import fit_common
import time
import requests
import tarfile
import shutil
import os
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from json import loads, dumps, dump
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


@attr(regression=False, smoke=True, skus_api2_tests=True)
class SkusTests(fit_common.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.clear()
        cls.__nodes = []
        cls.__sku_id = ""
        cls.__workflows = {}
        cls.__tasks = {}
        cls.__config_json = {}
        cls.__rootDir = "/tmp/tarball/"
        cls.__skuPackTarball = cls.__rootDir + "mytest.tar.gz"

    @classmethod
    def tearDownClass(cls):
        cls.clear()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def test_skus(self):
        # """Testing GET:api/2.0/skus to get list of skus"""
        Api().skus_get()
        rsp = self.__client.last_response
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        loads(self.__client.last_response.data)

    # todo: should use api2_check-skus
    @depends(after='test_skus')
    def test_post_sku(self):
        # """Test POST:api/2.0/skus"""
        sku = {
            "name": "Quanta-D44",
            "rules": [
                {
                    "path": "dmi.Base Board Information.Manufacturer",
                    "contains": "Intel"
                },
                {
                    "path": "ohai.dmi.memory.total",
                    "equals": "32946864kB"
                }
            ],
            "discoveryGraphName": "Graph.InstallCoreOS",
            "discoveryGraphOptions": {
                "username": "testuser",
                "password": "hello",
                "hostname": "mycoreos"
            }
        }
        Api().skus_post(sku)
        data = self.__get_data()
        logs.debug(' Posted data %s', dumps(data, indent=4))
        logs.info(' Posted sku id %s', data['id'])
        for sku_key in sku.keys():
            self.assertEqual(sku[sku_key], data[sku_key], msg='Key "{}" not found'.format(sku_key))

        # set class level sku_id for patch test
        self.__class__.__sku_id = data['id']

        # POST the same SKU again and make sure that we get a 409
        try:
            Api().skus_post(sku)
        except ApiException as e:
            self.assertEqual(409, e.status, msg='Expected 409, received {}'.format(e.status))

    @depends(after='test_post_sku')
    def test_skus_id(self):
        # """Testing GET:api/2.0/skus/id to get specific catalog details"""
        Api().skus_get()
        found = False
        skus = loads(self.__client.last_response.data)
        for n in skus:
            sku_id = n.get('id')
            logs.info_6(' Checking sku id %s', sku_id)
            self.assertIsNotNone(sku_id)
            Api().skus_id_get(identifier=sku_id)
            rsp = self.__client.last_response
            self.assertEqual(200, rsp.status, msg=rsp.reason)
            if sku_id == self.__class__.__sku_id:
                found = True
        self.assertTrue(found, "POSTed sku {} not found".format(sku_id))

    @depends(after='test_skus_id')
    def test_skus_patch(self):
        # """Test PATCH:api/2.0/skus/:identifier"""
        logs.info(' Patching SKU %s ', self.__class__.__sku_id)
        patch_data = {
            "name": "Quanta-T55"
        }
        Api().skus_patch(self.__class__.__sku_id, patch_data)
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)

        self.assertEqual(200, result.status, msg=result.reason)
        self.assertEqual("Quanta-T55", data['name'])

        try:
            Api().skus_patch('does_not_exist', {})
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404, received {}'.format(e.status))

    @depends(after='test_skus_patch')
    def test_delete_skus(self):
        # """Test DELETE:api/2.0/skus/:identifier"""
        logs.info(' Deleting SKU %s', self.__class__.__sku_id)
        Api().skus_id_delete(identifier=self.__class__.__sku_id)
        result = self.__client.last_response
        self.assertEqual(204, result.status, msg=result.reason)

        # Check if sku was deleted
        try:
            Api().skus_id_get(identifier=self.__class__.__sku_id)
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404, received {}'.format(e.status))

        # Check delete of invalid id
        try:
            Api().skus_id_delete(identifier='does_not_exist')
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404, received {}'.format(e.status))

    def dont_run_get_sku_nodes(self):
        # """Test GET /api/2.0/skus/:identifier/nodes"""
        sku = {
            "name": "mytestsku",
            "rules": [
                {
                    "path": "dmi.Base Board Information.Manufacturer",
                    "contains": " "
                }
            ]
        }

        Api().nodes_get_all()
        self.__class__.__nodes = loads(self.__client.last_response.data)

        for node in self.__class__.__nodes:
            if node.get('type') == 'compute':
                # update the sku rule above (rules[0].name.contains) with a value from the cataloged node
                node_id = node.get('id')
                logs.info("Nodeid %s", node_id)
                Api().nodes_get_catalog_source_by_id(identifier=node_id, source='dmi')
                node_catalog_data = loads(self.__client.last_response.data)
                # logs.info('node_manufacturer is  :  %s ', node_catalog_data)
                if len(node_catalog_data) > 0:
                    logs.info('node_manufacturer is: %s',
                              node_catalog_data.get('data').get("Base Board Information").get("Manufacturer"))
                    node_manufacturer = node_catalog_data \
                        .get('data').get("Base Board Information").get("Manufacturer").split(" ")[0]
                    sku['rules'][0]['contains'] = node_manufacturer

                    # POST the new sku
                    logs.info("posting SKU : %s", sku)
                    Api().skus_post(sku)
                    result = self.__client.last_response
                    data = loads(self.__client.last_response.data)
                    sku_id = data['id']
                    logs.info("ID of the posted sku is: %s", sku_id)
                    self.assertEqual(201, result.status, msg=result.reason)
                    logs.info("node_id %s", node_id)

                    # Give enough time to wait the sku discovery finishes
                    time.sleep(3)
                    retries = 10
                    while retries > 0:
                        self.assertEqual(201, result.status, msg=result.reason)
                        logs.info("node_id %s", node_id)

                        # Validate that the sku element in the node has been updated with the right sku ID
                        Api().nodes_get_by_id(identifier=node_id)
                        updated_node = loads(self.__client.last_response.data)
                        if updated_node['sku'] is not None:
                            logs.info("updated_node is: %s", updated_node)
                            arr = updated_node['sku'].split("/")
                            if sku_id == arr[4]:
                                logs.info("updated_node is : %s", updated_node)
                                break
                        retries = retries - 1
                        if retries == 0:
                            self.fail("The node {} never be assigned with the new sku {}".format(node_id, sku_id))
                            # raise Error("The node {0} never be assigned with the new sku {1}".format(node_id, sku_id))
                        else:
                            logs.info("Wait more time to let new sku take effect, remaining %s retries", retries)
                            time.sleep(1)

                    # validate the /api/2.0/skus/:id/nodes works
                    Api().skus_id_get_nodes(sku_id)
                    result = self.__client.last_response
                    data = loads(self.__client.last_response.data)
                    self.assertEqual(200, result.status, msg=result.reason)
                    flag = False
                    for item in data:
                        if item["id"] == node_id:
                            flag = True
                            break
                    self.assertTrue(flag, msg='Node id {} not found'.format(node_id))

                    # delete the sku that where created
                    logs.info(" Deleting the added sku of %s", sku_id)
                    Api().skus_id_delete(identifier=sku_id)
                    result = self.__client.last_response
                    self.assertEqual(204, result.status, msg=result.reason)

    # @depends(after='test_get_sku_nodes')
    @depends(after='test_delete_skus')
    def test_post_skupack(self):
        # """Test POST:api/2.0/skus/pack"""
        Api().nodes_get_all()
        self.__class__.__nodes = loads(self.__client.last_response.data)
        logs.debug_6(" class nodes %s", self.__class__.__nodes)
        for node in self.__class__.__nodes:
            if node.get('type') == 'compute':
                break

        if node:
            # update the sku rule above (rules[0].name.contains) with a value from the cataloged node
            node_id = node.get('id')
            logs.info(" Node_id %s ", node_id)
            Api().nodes_get_catalog_source_by_id(identifier=node_id, source='dmi')
            node_catalog_data = loads(self.__client.last_response.data)
            if len(node_catalog_data) > 0:
                node_manufacturer = node_catalog_data \
                    .get('data').get("System Information").get("Manufacturer").split(" ")[0]
                logs.info(" node %s Man %s", node_id, node_manufacturer)

                # Post the sku pack
                self.generateTarball(node_manufacturer)
                self.__file = {'file': open(self.__skuPackTarball, 'rb')}
                URL = config.host + config.api_root + '/skus/pack'
                logs.info("URL %s", URL)
                requests.adapters.DEFAULT_RETRIES = 3

                for n in range(0, 5):
                    res = None
                    try:
                        logs.info("Number of attempts to POST the skupack: %s", n + 1)
                        res = requests.post(URL, files=self.__file)
                        break
                    except requests.ConnectionError as err:
                        logs.info("Request Error: %s", str(err))

                self.assertIsNotNone(res, msg='Connection could not be established')
                self.assertEqual(201, res.status_code, msg=res.reason)
                self.__packFolderId = res.text.split('"')[3]

                # Validate that the pack content of workflows has been posted
                win_str = '{}::{}'.format(self.__class__.__workflows.get("injectableName"), self.__packFolderId)
                logs.info('Workflow injectable name: %s', win_str)
                Api().workflows_get_graphs_by_name(win_str)
                result = self.__client.last_response
                loads(self.__client.last_response.data)
                self.assertEqual(200, result.status, msg=res.reason)

                # Validate that the pack content of tasks has been posted
                tin_str = '{}::{}'.format(self.__class__.__tasks.get("injectableName"), self.__packFolderId)
                logs.info(tin_str)
                Api().workflows_get_tasks_by_name(tin_str)
                result = self.__client.last_response
                loads(self.__client.last_response.data)
                self.assertEqual(200, result.status, msg=res.reason)

                # Check for skupack templates
                sku_id = res.json()['id']
                Api().templates_meta_get_by_name('template.json', scope=sku_id)
                self.assertEqual(200, self.__client.last_response.status)
                self.assertEqual(1, len(loads(self.__client.last_response.data)))

                # Check for skupack profiles
                Api().profiles_get_metadata_by_name('useless.json', scope=sku_id)
                self.assertEqual(200, self.__client.last_response.status)
                self.assertEqual(1, len(loads(self.__client.last_response.data)))

                # """Test DELETE:api/2.0/skus/:identifier/pack"""
                Api().skus_id_get(identifier=self.__packFolderId)
                result = self.__client.last_response
                self.assertEqual(200, result.status,
                                 msg="skus_id_get: expected 200, received {0}".format(result.status))

                logs.info("SkuPack FolderId to delete %s", self.__packFolderId)
                Api().skus_id_delete_pack(identifier=self.__packFolderId)
                result = self.__client.last_response
                self.assertEqual(204, result.status,
                                 msg="sku pack folder delete failed, expected {}, received {}, reason {}"
                                 .format(200, result.status, result.reason))

                # check to see if skuPack related key is None after the delete pack
                Api().skus_get()
                skus = loads(self.__client.last_response.data)
                for sku in skus:
                    self.assertEqual(None, sku.get('httpProfileRoot'))
                Api().skus_id_delete(self.__packFolderId)
                result = self.__client.last_response
                self.assertEqual(204, result.status,
                                 msg="sku id delete failed, expected {}, received {}, reason {}"
                                 .format(204, result.status, result.reason))

                # check to see if sku contents are cleaned up
                try:
                    Api().skus_id_get(identifier=self.__packFolderId)
                    self.fail(msg="packFolderId {0} was not expected".format(self.__packFolderId))
                except ApiException as e:
                    result = self.__client.last_response
                    self.assertEqual(404, e.status,
                                     msg="status = {1}, packFolderId {0} was not expected"
                                     .format(self.__packFolderId, e.status))

    @depends(after='test_post_skupack')
    def test_put_skupack(self):
        # """Test PUT:api/2.0/skus/pack"""

        # Post the sku pack
        self.generateTarball("Non Quanta")
        self.__file = {'file': open(self.__skuPackTarball, 'rb')}
        logs.info("****** The POST SKU pack is : %s ", self.__skuPackTarball)
        URL = config.host + config.api_root + '/skus/pack'

        requests.adapters.DEFAULT_RETRIES = 3
        res = None
        try:
            logs.info("Posting SKU PACK")
            res = requests.post(URL, files=self.__file)
        except requests.ConnectionError as e:
            logs.info("POST Failed. status: %s, Message: %s", e.status, e.message)
            return

        # sku pack posted
        logs.info("****** Posted sku pack: %s", res.text)
        self.assertIsNotNone(res, msg='POST: Connection could not be established')
        self.assertEqual(201, res.status_code, msg="expected 201, received {0}".format(res.status_code))
        self.__packFolderId = res.text.split('"')[3]

        logs.info(" FolderId: %s ", self.__packFolderId)

        # PUT the sku pack
        URL = config.host + '/api/2.0/skus/' + self.__packFolderId + '/pack'
        logs.info("******  The PUT URL is %s: ", URL)
        logs.info(" The SKU pack is : %s ", self.__skuPackTarball)

        requests.adapters.DEFAULT_RETRIES = 3
        res = None
        try:
            with open(self.__skuPackTarball) as fh:
                mydata = fh.read()
                res = requests.put(URL, data=mydata, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        except requests.ConnectionError as e:
            logs.info("PUT Failed. status: %s, Message: %s", e.status, e.message)
            return

        self.assertIsNotNone(res, msg='PUT: Connection could not be established')
        self.assertEqual(201, res.status_code, msg="expected 201, received {0}".format(res.status_code))

        # sku ids should match from POST and PUT
        putId = res.text.split('"')[3]
        self.assertEqual(self.__packFolderId, putId, "sku pack ids don't match after post followed by put")

        # Clean up
        logs.info("SkuPack FolderId to delete %s", self.__packFolderId)
        Api().skus_id_delete_pack(identifier=self.__packFolderId)
        result = self.__client.last_response
        self.assertEqual(204, result.status,
                         msg="sku pack folder delete failed, expected {0}, received {1}, reason {2}"
                         .format(204, result.status, result.reason))

        logs.info("skupack id delete: %s", self.__packFolderId)
        Api().skus_id_delete(self.__packFolderId)
        result = self.__client.last_response
        self.assertEqual(204, result.status,
                         msg="sku pack delete failed, expected {0}, received {1}, reason {2}"
                         .format(204, result.status, result.reason))

    def generateTarball(self, ruleUpdate=None):

        current_dir = os.getcwd()
        if os.path.isdir(self.__rootDir):
            shutil.rmtree(self.__rootDir)
        os.mkdir(self.__rootDir)
        tarballDirs = ["profiles", "static", "tasks", "templates", "workflows"]
        for dir in tarballDirs:
            os.mkdir(self.__rootDir + dir)

        self.__class__.__config_json = {
            "name": "Quanta X41",
            "rules": [
                {
                    "path": "dmi.Base Board Information.Manufacturer",
                    "contains": "Quanta"
                }
            ],
            "skuConfig": {
                "value1": {
                    "value": "value"
                }
            },
            "workflowRoot": "workflows",
            "taskRoot": "tasks",
            "httpProfileRoot": "profiles",
            "httpTemplateRoot": "templates",
            "httpStaticRoot": "static"
        }
        if ruleUpdate is not None:
            self.__class__.__config_json['rules'][0]['contains'] = ruleUpdate

        with open(self.__rootDir + 'config.json', 'w') as f:
            dump(self.__class__.__config_json, f)
        f.close()

        self.__class__.__tasks = {
            "friendlyName": "Flash Quanta BMC",
            "injectableName": "Task.Linux.Flash.unique.Bmc",
            "implementsTask": "Task.Base.Linux.Commands",
            "options": {
                "file": None,
                "downloadDir": "/opt/downloads",
                "commands": [
                    "sudo /opt/socflash/socflash_x64 -b /opt/uploads/bmc-backup.bin",
                    "sudo curl -T /opt/uploads/bmc-backup.bin {{ api.files }}/{{ task.nodeId }}-bmc-backup.bin",
                    "sudo /opt/socflash/socflash_x64 -s option=x flashtype=2 if={{ options.downloadDir }}/{{ options.file }}"
                ]
            },
            "properties": {
                "flash": {
                    "type": "bmc",
                    "vendor": {
                        "quanta": {}
                    }
                }
            }
        }
        with open(self.__rootDir + '/tasks/tasks.json', 'w') as f:
            dump(self.__class__.__tasks, f)
        f.close()

        self.__class__.__workflows = {
            "friendlyName": "noop-sku-graph",
            "injectableName": "Graph.noop-example",
            "tasks": [
                {
                    "label": "noop-1",
                    "taskName": "Task.noop"
                },
                {
                    "label": "noop-2",
                    "taskName": "Task.noop",
                    "waitOn": {
                        "noop-1": "finished"
                    }
                }
            ]
        }
        with open(self.__rootDir + '/workflows/workflows.json', 'w') as f:
            dump(self.__class__.__workflows, f)
        f.close()

        self.__template = {
            "friendlyName": "Flash Quanta BMC",
            "injectableName": "Task.Linux.Flash.unique.Bmc",
            "implementsTask": "Task.Base.Linux.Commands",
            "options": {
                "file": None,
                "downloadDir": "/opt/downloads",
                "commands": [
                    "sudo /opt/socflash/socflash_x64 -b /opt/uploads/bmc-backup.bin",
                    "sudo curl -T /opt/uploads/bmc-backup.bin {{ api.files }}/{{ task.nodeId }}-bmc-backup.bin",
                    "sudo /opt/socflash/socflash_x64 -s option=x flashtype=2 if={{ options.downloadDir }}/{{ options.file }}"
                ]
            },
            "properties": {
                "flash": {
                    "type": "bmc",
                    "vendor": {
                        "quanta": {}
                    }
                }
            }
        }
        with open(self.__rootDir + 'templates/template.json', 'w') as f:
            dump(self.__template, f)
        f.close()

        self.__profile = {'useless': 'a useless profile'}
        with open(self.__rootDir + 'profiles/useless.json', 'w') as f:
            dump(self.__profile, f)
        f.close()

        os.chdir(self.__rootDir)
        with tarfile.open(name=self.__skuPackTarball, mode="w:gz") as f:
            for name in ["config.json", "profiles", "static", "tasks", "templates", "workflows"]:
                f.add(name)

        # restore the current directory to the run_tests.py dir
        # so it doesn't affect other tests
        os.chdir(current_dir)

    @classmethod
    def clear(self):
        """ Clear the test SKU IDs from the testbed """
        Api().skus_get()
        self.__client.last_response
        data = loads(self.__client.last_response.data)
        for item in data:
            if item['name'] in ['Quanta-D44', 'Quanta-T55', 'mytestsku', 'Quanta X41']:
                logs.info("Cleaning skus")
                logs.info(item.get("id"))
                Api().skus_id_delete(item.get("id"))
