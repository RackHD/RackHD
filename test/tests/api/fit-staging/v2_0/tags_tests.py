"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

"""
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from json import loads, dumps
from nose.plugins.attrib import attr
from nosedep import depends

logs = flogging.get_loggers()


# @test(groups=['tags_api2.tests'])
@attr(regression=False, smoke=True, lookups_api2_tests=True)
class TagsTests(fit_common.unittest.TestCase):
    def setUp(self):
        self.__client = config.api_client

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __create_tag_rule(self, id):
        Api().nodes_get_catalog_source_by_id(identifier=id, source='dmi')
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

    def test_tags_start_clean(self):
        # """ Clean up any pre-existing test tags"""
        logs.info("Deleting any tags created from previous script runs")
        all_tags = []
        Api().get_all_tags()
        rsp = self.__client.last_response
        all_tags = self.__get_data()
        if all_tags:
            Api().nodes_get_all()
            nodes = self.__get_data()
            for node in nodes:
                if node.get('type') == 'compute':
                    Api().delete_tag(tag_name=node.get('id'))
                    rsp = self.__client.last_response
                    self.assertEqual(204, rsp.status, msg=rsp.reason)
            Api().get_all_tags()
            rsp = self.__client.last_response
            all_tags = self.__get_data()
            self.assertEqual(200, rsp.status, msg=rsp.reason)
            self.assertEqual([], all_tags, msg='Tags were not deleted successfully')

    @depends(after='test_tags_start_clean')
    def test_tag_create(self):
        # """ Testing POST:/api/2.0/tags/ """
        Api().nodes_get_all()
        nodes = self.__get_data()
        for node in nodes:
            if node.get('type') == 'compute':
                tagsWithRules = self.__create_tag_rule(node.get('id'))
                self.assertNotEqual(len(tagsWithRules), 0, "Failed to create tag rules")
                logs.debug(dumps(tagsWithRules, indent=4))
                Api().create_tag(body=tagsWithRules)
                tag_data = self.__get_data()
                self.assertEqual(node.get('id'), tag_data["name"], "Failed creating tag")
        self.assertRaises(rest.ApiException, Api().create_tag, body='fooey')

    # @test(groups=['test-tags-api2'], depends_on_groups=['create-tag-api2'])
    @depends(after='test_tag_create')
    def test_tags(self):
        # """ Testing GET:/api/2.0/tags """
        Api().nodes_get_all()
        nodes = self.__get_data()
        tagsArray = []
        for n in nodes:
            if n.get('type') == 'compute':
                tagsWithRules = self.__create_tag_rule(n.get('id'))
                self.assertNotEqual(len(tagsWithRules), 0, "Failed to create tag rules")
                tagsArray.append(tagsWithRules)
        Api().get_all_tags()
        rsp = self.__client.last_response
        updated_tags = self.__get_data()
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        for i in xrange(len(updated_tags)):
            self.assertEqual(updated_tags[i]['rules'][0]['path'], 'dmi.System Information.Manufacturer',
                             msg='Tag {} has incorrect path: {}'.format(updated_tags[i],
                                                                        updated_tags[i]['rules'][0]['path']))

    # @test(groups=['test-tags-tagname-api2'], depends_on_groups=['test-tags-api2'])
    @depends(after='test_tags')
    def test_tags_tagname(self):
        # """ Testing GET:/api/2.0/tags/:tagName """
        Api().nodes_get_all()
        nodes = self.__get_data()
        for node in nodes:
            if node.get('type') == 'compute':
                Api().get_tag(tag_name=node.get("id"))
                rsp = self.__client.last_response
                tag = self.__get_data()
                self.assertEqual(200, rsp.status, msg=rsp.reason)
                self.assertEqual(tag.get('name'), node.get('id'),
                                 msg='Could not find the tag: {}'.format(node.get('id')))

    # @test(groups=['test-nodes-tagname-api2'], depends_on_groups=['test-tags-tagname-api2'])
    @depends(after='test_tags_tagname')
    def test_nodes_tagname(self):
        # """ Testing GET:/api/2.0/tags/:tagName/nodes """
        Api().nodes_get_all()
        nodes = self.__get_data()
        for node in nodes:
            Api().get_nodes_by_tag(tag_name=node.get('id'))
            nodesWithTags = self.__get_data()
            for tagged_node in nodesWithTags:
                if tagged_node.get('type') == 'compute':
                    nodesList = self.__get_data()
                    tagsList = nodesList[0]['tags']
                    self.assertIn(tagged_node.get('id'), tagsList,
                                  msg="Tag {} not in taglist for node {}".format(node.get('id'),
                                                                                 tagged_node.get('id')))

    # @test(groups=['test_tags_delete'], depends_on_groups=['test-nodes-tagname-api2'])
    @depends(after='test_nodes_tagname')
    def test_tags_del(self):
        # """ Testing DELETE:api/2.0/tags/:tagName """
        logs.info("Deleting tag that was created in Testing POST:/api/2.0/tags/")
        Api().nodes_get_all()
        nodes = self.__get_data()
        for node in nodes:
            if node.get('type') == 'compute':
                Api().delete_tag(tag_name=node.get('id'))
                rsp = self.__client.last_response
                self.assertEqual(204, rsp.status, msg=rsp.reason)
        Api().get_all_tags()
        rsp = self.__client.last_response
        updated_tags = self.__get_data()
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        self.assertEqual([], updated_tags, msg='Tags were not deleted successfully')
