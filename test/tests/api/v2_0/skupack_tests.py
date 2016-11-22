from config.api2_0_config import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from proboscis.asserts import *
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads
from on_http_api2_0 import rest
import time
import requests
import os
import subprocess
import json
import tarfile
import shutil


LOG = Log(__name__)


@test(groups=['skus_api2.tests'])
class SkusTests(object):
    def __init__(self):

        self.__client = config.api_client
        self.clear()
        self.__nodes= []
        self.__sku_id = ""
        self.__workflows = {}
        self.__tasks ={}
        self.__config_json = {}
        self.__rootDir ="/tmp/tarball/"
        self.__skuPackTarball =  self.__rootDir +"mytest.tar.gz"

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['api2_get-skus'])
    def test_skus(self):
        """Testing GET:api/2.0/skus to get list of skus"""
        Api().skus_get()
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)
        data = loads(self.__client.last_response.data)

    @test(groups=[ 'api2_post_skus'], depends_on_groups=['api2_check-skus'])
    def post_sku(self):
        """Test POST:api/2.0/skus"""
        sku =   {
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
        for key in sku.keys():
                assert_equal(sku[key], data[key])

        #POST the same SKU again and make sure that we get a 409
        try:
            Api().skus_post(sku)
        except ApiException as e:
            assert_true(409, e.status)

    @test(groups=['api2_get_skus_by_id' ], depends_on_groups=['api2_post_skus'])
    def test_skus_id(self):
        """Testing GET:api/2.0/skus/id to get specific catalog details"""
        Api().skus_get()
        skus = loads(self.__client.last_response.data)
        for n in skus:
            self.__sku_id  = n.get('id')
            assert_is_not_none(self.__sku_id)
            Api().skus_id_get(identifier=self.__sku_id)
            rsp = self.__client.last_response
            assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['api2_patch_skus'], depends_on_groups=['api2_get_skus_by_id'])
    def skus_patch(self):
        """Test PATCH:api/2.0/skus/:identifier"""
        patch_data = {
            "name": "Quanta-T55"
        }
        Api().skus_patch(self.__sku_id, patch_data)
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)

        assert_equal(200, result.status, message=result.reason)
        assert_equal("Quanta-T55", data['name'])

        try:
            Api().skus_patch('does_not_exist', {})
        except ApiException as e:
            assert_true(404, e.status)

    @test(groups=['api2_delete_skus'], depends_on_groups=['api2_patch_skus'])
    def delete_skus(self):
        """Test DELETE:api/2.0/skus/:identifier"""

        Api().skus_id_delete(identifier = self.__sku_id)
        result = self.__client.last_response
        assert_equal(204, result.status, message=result.reason)

        try:
            Api().skus_id_get(identifier = self.__sku_id)
        except ApiException as e:
            assert_true(404, e.status)

        try:
            Api().skus_id_delete(identifier='does_not_exist')
        except ApiException as e:
            assert_true(404, e.status)

    @test(groups=['api2_get_sku_nodes'], depends_on_groups=['api2_delete_skus'])
    def get_sku_nodes(self):
        """Test GET /api/2.0/skus/:identifier/nodes"""
        sku=   {
            "name": "mytestsku",
            "rules": [
                {
                    "path": "dmi.Base Board Information.Manufacturer",
                    "contains": " "
                }
            ]
        }

        Api().nodes_get_all()
        self.__nodes = loads(self.__client.last_response.data)
        i =0
        for n in self.__nodes:
            if n.get('type') == 'compute':
                #update the sku rule above (rules[0].name.contains) with a value from the cataloged node
                node_id = n.get('id')
                Api().nodes_get_catalog_source_by_id(identifier=node_id,source='dmi')
                node_catalog_data =loads(self.__client.last_response.data)
                #LOG.info('node_manufacturer is  :  {0} '.format((node_catalog_data)))
                if len(node_catalog_data) > 0:
                    LOG.info('node_manufacturer is  :  {0} '.format(node_catalog_data.get('data').get("Base Board Information").get("Manufacturer")))
                    node_manufacturer= node_catalog_data.get('data').get("Base Board Information").get("Manufacturer").split(" ")[0]
                    sku['rules'][0]['contains'] = node_manufacturer

                    #POST the new sku
                    LOG.info("posting SKU : {0}".format(sku))
                    Api().skus_post(sku)
                    result = self.__client.last_response
                    data = loads(self.__client.last_response.data)
                    sku_id = data['id']
                    LOG.info("ID of the posted sku is:   "+ sku_id)
                    time.sleep(3)
                    assert_equal(201, result.status, message=result.reason)
                    LOG.info("node_id " + node_id)

                    #Validate that the sku element in the node has been updated with the right sku ID
                    Api().nodes_get_by_id(identifier=node_id)
                    updated_node = loads(self.__client.last_response.data)
                    LOG.info("updated_noded is : {0}".format(updated_node))
                    arr =updated_node['sku'].split("/")
                    assert_equal(sku_id, arr[4])

                    #validate the /api/2.0/skus/:id/nodes works
                    Api().skus_id_get_nodes(sku_id)
                    result = self.__client.last_response
                    data = loads(self.__client.last_response.data)
                    assert_equal(200, result.status, message=result.reason)
                    flag = False
                    for item in data:
                        if item["id"] ==  node_id:
                            flag = True
                            break
                    assert_true(flag)

                    #delete the sku that where created
                    LOG.info("Deleting the added sku")
                    Api().skus_id_delete(identifier=sku_id)
                    result = self.__client.last_response
                    assert_equal(204, result.status, message=result.reason)
            i = i +1

    @test(groups=['api2_post_skupack'], depends_on_groups=['api2_get_sku_nodes'])
    def post_skupack(self):
        """Test POST:api/2.0/skus/pack"""
        for n in self.__nodes:
            if n.get('type') == 'compute':
                # update the sku rule above (rules[0].name.contains) with a value from the cataloged node
                node_id = n.get('id')
                Api().nodes_get_catalog_source_by_id(identifier=node_id,source='dmi')
                node_catalog_data =loads(self.__client.last_response.data)
                if len(node_catalog_data) > 0:
                    node_manufacturer = node_catalog_data.get('data').get("System Information").get("Manufacturer").split(" ")[0]

                    #Post the sku pack
                    self.generateTarball(node_manufacturer)
                    self.__file = {'file': open(self.__skuPackTarball, 'rb')}
                    URL = config.host + config.api_root + '/skus/pack'
                    LOG.info("URL {0}".format(URL))
                    requests.adapters.DEFAULT_RETRIES = 3
                    for n in range (0,5):
                            try:
                                LOG.info("Number of attempt to post  the skupack :  {0}".format(n))
                                res = requests.post(URL, files=self.__file)
                                break
                            except requests.ConnectionError, e:
                                LOG.info("Request Error {0}: ".format(e))
                    assert_equal(201, res.status_code, message=res.reason)
                    self.__packFolderId = res.text.split('"')[3]

                    #Validate that the pack content of workflows has been posted
                    LOG.info('Workflow injectable name : {0}'.format(self.__workflows.get("injectableName") + "::" +  self.__packFolderId))
                    Api().workflows_get_graphs_by_name(self.__workflows.get("injectableName") + "::" + self.__packFolderId)
                    result = self.__client.last_response
                    data = loads(self.__client.last_response.data)
                    assert_equal(200, result.status, message=res.reason)

                    #Validate that the pack content of tasks has been posted
                    LOG.info(self.__tasks.get("injectableName") + "::" + self.__packFolderId)
                    Api().workflows_get_tasks_by_name(self.__tasks.get("injectableName") + "::" + self.__packFolderId)
                    result = self.__client.last_response
                    data = loads(self.__client.last_response.data)
                    assert_equal(200, result.status, message=res.reason)

                    # Check for skupack templates
                    sku_id = res.json()['id']
                    Api().templates_meta_get_by_name('template.json', scope=sku_id )
                    assert_equal(200, self.__client.last_response.status)
                    assert_equal(1, len(loads(self.__client.last_response.data)))

                    # Check for skupack profiles
                    Api().profiles_get_metadata_by_name('useless.json', scope=sku_id)
                    assert_equal(200, self.__client.last_response.status)
                    assert_equal(1, len(loads(self.__client.last_response.data)))
                    
                    """Test DELETE:api/2.0/skus/:identifier/pack"""
                    Api().skus_get()
                    skus = loads(self.__client.last_response.data)
                    LOG.info("Printing Sku from get skus before a delete sku pack")
                    LOG.info(skus)
                    Api().skus_id_delete_pack(self.__packFolderId)
                    # check to see if skuPack related key is None after the delete pack 
                    Api().skus_get()
                    skus = loads(self.__client.last_response.data)
                    for n in skus:
                        LOG.info(n.get('httpProfileRoot'))
                        assert_equal(None, n.get('httpProfileRoot'))
                    Api().skus_id_delete(self.__packFolderId)
                    result = self.__client.last_response
                    assert_equal(204, result.status, message=result.reason)
                    # check to see if sku contents are cleaned up
                    Api().skus_get()
                    skus = loads(self.__client.last_response.data)
                    LOG.info("List of Skus after delete sku pack")
                    LOG.info(skus)
                    assert_equal(0, len(skus))
                    
                     
    @test(groups=['api2_put_skupack'], depends_on_groups=['api2_post_skupack'])
    def put_skupack(self):
        """Test PUT:api/2.0/skus/pack"""
        for n in self.__nodes:
            if n.get('type') == 'compute':
                node_id = n.get('id')
                Api().nodes_get_catalog_source_by_id(identifier=node_id,source='dmi')
                node_catalog_data =loads(self.__client.last_response.data)
                if len(node_catalog_data) > 0:
                    # update the sku rule above (rules[0].name.contains) with a value from the cataloged node
                    node_id = n.get('id')
                    # Post the sku pack
                    self.generateTarball("Non Quanta")
                    self.__file = {'file': open(self.__skuPackTarball, 'rb')}
                    URL = config.host + config.api_root + '/skus/pack'
                    requests.adapters.DEFAULT_RETRIES = 3
                    for n in range(0, 5):
                        try:
                            LOG.info("Attempt to post number {0}".format(n))
                            res = requests.post(URL, files=self.__file)
                            break
                        except requests.ConnectionError, e:
                            print e
                    assert_equal(201, res.status_code, message=res.reason)
                    self.__packFolderId = res.text.split('"')[3]

                    # PUT the sku pack
                    URL = config.host + '/skus/' + self.__packFolderId + '/pack'
                    LOG.info("The URL is : " + URL)
                    self.__file = {'file': open(self.__skuPackTarball, 'rb')}
                    requests.adapters.DEFAULT_RETRIES = 3
                    for n in range(0, 5):
                        try:
                            res = requests.request('PUT', URL, files=self.__file)
                            break
                        except requests.ConnectionError, e:
                            print e
                            assert_equal(200, res.status_code, message=res.reason)

                    #Clean up
                    Api().skus_id_delete_pack(self.__packFolderId)
                    Api().skus_id_delete(self.__packFolderId)

    def generateTarball(self, ruleUpdate= None):
        current_dir = os.getcwd()
        if os.path.isdir(self.__rootDir ):
            shutil.rmtree(self.__rootDir )
        os.mkdir(self.__rootDir )
        tarballDirs = ["profiles", "static", "tasks", "templates", "workflows"]
        for dir in tarballDirs:
            os.mkdir(self.__rootDir  + dir)


        self.__config_json = {
            "name": "Quanta T41",
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
        if (ruleUpdate != None):
            self.__config_json['rules'][0]['contains'] = ruleUpdate

        with open(self.__rootDir  + 'config.json', 'w') as f:
            json.dump(self.__config_json, f)
        f.close()

        self.__tasks = {
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
            json.dump(self.__tasks, f)
        f.close()

        self.__workflows = {
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
                    "waitOn" : {
                        "noop-1" :"finished"
                    }
                }
            ]
        }
        with open(self.__rootDir  + '/workflows/workflows.json', 'w') as f:
            json.dump(self.__workflows, f)
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
            json.dump(self.__template, f)
        f.close()

        self.__profile = { 'useless': 'a useless profile' }
        with open(self.__rootDir + 'profiles/useless.json', 'w') as f:
            json.dump(self.__profile, f)
        f.close()

        os.chdir(self.__rootDir )
        with tarfile.open(self.__rootDir + "mytest.tar.gz", mode ="w:gz") as f:
            for name in ["config.json", "profiles", "static", "tasks", "templates", "workflows"]:
                f.add(name)

        #restore the current directory to the run.py dir
        #so it doesn't affect other tests
        os.chdir(current_dir)

    def clear(self):
        Api().skus_get()
        rsp = self.__client.last_response
        data = loads(self.__client.last_response.data)
        for item in data:
            LOG.info(item.get("id"))
            Api().skus_id_delete(item.get("id"))
