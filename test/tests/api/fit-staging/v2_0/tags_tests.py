from config.api2_0_config import config
from config.amqp import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis import test
from proboscis.asserts import assert_raises
from nodes_tests import NodesTests
from json import loads
from json import dumps
from time import sleep

LOG = Log(__name__)

@test(groups=['tags_api2.tests'])
class TagsTests(object):
    def __init__(self):
        self.__client = config.api_client

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __create_tag_rule(self, id):
        Api().nodes_get_catalog_source_by_id(identifier=id,source='dmi')
        updated_catalog = self.__get_data()
        return {
            "name": id,
            "rules": [
                {
                    "equals": updated_catalog["data"]["System Information"]["Manufacturer"],
                    "path": "dmi.System Information.Manufacturer" 
                }
            ]
        }

    @test(groups=['create-tag-api2'])
    def test_tag_create(self):
        """ Testing POST:/api/2.0/tags/ """
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                tagsWithRules = self.__create_tag_rule(n.get('id'))
                assert_not_equal(len(tagsWithRules), 0, "Failed to create tag rules")
                LOG.info(tagsWithRules)
                Api().create_tag(body=tagsWithRules)
                tag_data = self.__get_data()
                assert_equal(n.get('id'), tag_data["name"], "Failed creating tag")
        assert_raises(rest.ApiException, Api().create_tag, body='fooey')

    @test(groups=['test-tags-api2'], depends_on_groups=['create-tag-api2'])
    def test_tags(self):
        """ Testing GET:/api/2.0/tags """
        Api().nodes_get_all()
        nodes = self.__get_data()
        tagsArray = []
        for n in nodes:
            if n.get('type') == 'compute':
                tagsWithRules = self.__create_tag_rule(n.get('id'))
                assert_not_equal(len(tagsWithRules), 0, "Failed to create tag rules")
                tagsArray.append(tagsWithRules)
        Api().get_all_tags()
        rsp = self.__client.last_response
        updated_tags = self.__get_data()
        assert_equal(200, rsp.status, message=rsp.reason)
        for i in xrange(len(updated_tags)):
            assert_equal(updated_tags[i]['rules'][0]['path'], 'dmi.System Information.Manufacturer', message='Could not find the tag')

    @test(groups=['test-tags-tagname-api2'], depends_on_groups=['test-tags-api2'])
    def test_tags_tagname(self):
        """ Testing GET:/api/2.0/tags/:tagName """
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().get_tag(tag_name=n.get("id"))
                rsp = self.__client.last_response
                tag = self.__get_data()
                assert_equal(200, rsp.status, message=rsp.reason)
                assert_equal(tag.get('name'), n.get('id'), message='Could not find the tag')

    @test(groups=['test-nodes-tagname-api2'], depends_on_groups=['test-tags-tagname-api2'])
    def test_nodes_tagname(self):
        """ Testing GET:/api/2.0/tags/:tagName/nodes """
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            Api().get_nodes_by_tag(tag_name=n.get('id'))
            nodesWithTags = self.__get_data()
            for n in nodesWithTags:
                if n.get('type') == 'compute':
                    rsp = self.__client.last_response
                    nodesList = self.__get_data()
                    tagsList = nodesList[0]['tags']
                    checkTag = n.get('id') in tagsList
                    assert_equal(True, checkTag, message=rsp.reason)

    @test(groups=['test_tags_delete'], depends_on_groups=['test-nodes-tagname-api2'])
    def test_tags_del(self):
        """ Testing DELETE:api/2.0/tags/:tagName """
        LOG.info("Deleting tag that was created in"
                 " Testing POST:/api/2.0/tags/ ")
        Api().nodes_get_all()
        nodes = self.__get_data()
        for n in nodes:
            if n.get('type') == 'compute':
                Api().delete_tag(tag_name=n.get('id'))
                rsp = self.__client.last_response
                assert_equal(204, rsp.status, message=rsp.reason)
                Api().get_all_tags()
                rsp = self.__client.last_response
                updated_tags = self.__get_data()
                assert_equal(200, rsp.status, message=rsp.reason)
        assert_equal([],updated_tags, message='Tags were not deleted successfully')


