from config.api2_0_config import config
from config.amqp import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from proboscis.asserts import assert_equal
from proboscis import test
from proboscis.asserts import assert_raises
from nodes_tests import NodesTests
from json import loads
from time import sleep

LOG = Log(__name__)

@test(groups=['tags_api2.tests'])
class TagsTests(object):
    def __init__(self):
        self.__client = config.api_client
        self.__test_tagWithRules = {"name": "test-tag",
                                    "rules": [{"equals": "Testing testing",
                                               "path": "fooeyPath.Test Information.fooey"}]}
    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['create-tag-api2'])
    def test_tag_create(self):
        """ Testing POST:/api/2.0/tags/ """
        tagsWithRules = {"name": "new-tag",
                         "rules": [{"equals": "QuantaPlex T41S-2U",
                                    "path": "dmi.System Information.Product Name"}]}
        LOG.info('Creating tag (name={0})'.format(tagsWithRules))
        Api().create_tag(body=tagsWithRules)
        rsp = self.__client.last_response
        LOG.info("Printing response")
        LOG.info(rsp.status, json=False)
        assert_equal(201, rsp.status, message=rsp.reason)

    @test(groups=['test-tags-api2'], depends_on_groups=['create-tag-api2'])
    def test_tags(self):
        """ Testing GET:/api/2.0/tags """
        Api().get_all_tags()
        tags = self.__get_data()
        LOG.info(tags, json=True)
        rsp = self.__client.last_response
        LOG.info("Printing response")
        LOG.info(rsp.status, json=False)
        assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['test-tags-tagname-api2'], depends_on_groups=['test-tags-api2'])
    def test_tags_tagname(self):
        """ Testing GET:/api/2.0/tags/:tagName """
        Api().get_tag(tag_name="new-tag")
        tag = self.__get_data()
        LOG.info(tag, json=True)
        rsp = self.__client.last_response
        LOG.info("Printing response")
        LOG.info(rsp.status, json=False)
        assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['test-nodes-tagname-api2'], depends_on_groups=['test-tags-tagname-api2'])
    def test_nodes_tagname(self):
        """ Testing GET:/api/2.0/tags/:tagName/nodes """
        #NodesTests().test_node_tags_patch()
        Api().get_nodes_by_tag(tag_name="new-tag")
        nodes = self.__get_data()
        for n in nodes:
            LOG.info(n.get('id'), json=True)
        rsp = self.__client.last_response
        LOG.info("Printing response")
        LOG.info(rsp.status, json=False)
        assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['test_tags_delete'], depends_on_groups=['test-nodes-tagname-api2'])
    def test_tags_del(self):
        """ Testing DELETE:api/2.0/tags/:tagName """
        LOG.info('Creating test-tag to delete later(name={0})'.format(self.__test_tagWithRules))
        Api().create_tag(body=self.__test_tagWithRules)
        rsp = self.__client.last_response
        LOG.info("Printing response")
        LOG.info(rsp.status, json=False)
        Api().delete_tag(tag_name="test-tag")
        rsp = self.__client.last_response
        LOG.info(rsp.status, json=False)
        assert_equal(204, rsp.status, message=rsp.reason)


