'''
Copyright 2015, EMC, Inc.

Author(s):
Harry Ling

'''

import os
import sys
import json
import time
import string
import random
import urllib
from datetime import *
import time
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common
import test_api_utils

# Local methods
MON_NODES = fit_common.node_select()
MON_API_VERSION = 2.0

#clear the test environment
def tear_down():
    str_taglist = get_tag_list()
    taglist = json.loads(str_taglist)
    for tagitem in taglist:
        tagname = tagitem['name']
        delete_response = delete_tag(tagname)
        if delete_response not in range(200,205):
            print "Fail to clear up the tag-"+ tagname
            return 1
    nodes_list = get_node_id_list()
    for node in nodes_list:
        tags = get_tag_list_on_node(node)
        tag_list = json.loads(tags)
        for tag in tag_list:
            print "{} has tags: {}".format(node,tag)
            response = delete_tag_in_node(node,tag)
            if response  not in range(200,205):
                print "Fail to delete the tag:" + tag
                return 2
    print "clear the environment finished!"
    return 0

def get_node_list_by_sku(skuname):
    response = fit_common.rackhdapi("/api/{}/skus".format(MON_API_VERSION))
    skus = json.loads(response['text'])
    idfound = []
    for sku in skus:
        if skuname == sku['name']:
            sku_id = sku['id']
    response = fit_common.rackhdapi('/api/{}/nodes'.format(MON_API_VERSION))
    nodes = json.loads(response['text'])
    for node in nodes:
        if MON_API_VERSION == 1.1:
            if node.has_key('sku') and node['sku'] == sku_id:
                idfound.append(node['id'])
        if MON_API_VERSION == 2.0:
            if node.has_key('sku') and node['sku'].split('/')[-1] == sku_id:
                idfound.append(node['id'])
    return idfound
    
def delete_tag(tag_name):
    url_name = urllib.quote(tag_name,"")
    mon_url = "/api/{}/tags/{}".format(MON_API_VERSION,url_name)
    response_tag = fit_common.rackhdapi(mon_url,action='delete')
    return response_tag["status"]

def create_tag(json_tag_content):
    mon_url = '/api/{}/tags'.format(MON_API_VERSION)
    response_create_tag = fit_common.rackhdapi(mon_url,action='post',payload=json_tag_content)
    return response_create_tag["status"]

def get_tag(tag_name):
    url_name = urllib.quote(tag_name,"")
    mon_url = '/api/{}/tags/{}'.format(MON_API_VERSION,url_name)
    response_tag = fit_common.rackhdapi(mon_url)
    return response_tag['text']

def get_node_by_tag(tag_name):
    url_name = urllib.quote(tag_name,"")
    mon_url = '/api/{}/tags/{}/nodes'.format(MON_API_VERSION,url_name)
    response_tag = fit_common.rackhdapi(mon_url)
    if response_tag['status'] in range(200,205):
        return response_tag['text']
    else:
        return response_tag['status']

def get_tag_list():
    mon_url = '/api/{}/tags'.format(MON_API_VERSION)
    response_tag = fit_common.rackhdapi(mon_url)
    return response_tag['text']

def get_tag_list_on_node(nodeid):
    mon_url = '/api/{}/nodes/{}/tags/'.format(MON_API_VERSION,nodeid)
    response_tag = fit_common.rackhdapi(mon_url)
    return response_tag['text']

def post_workflow_to_nodes_by_tag(tag_name,workflowname,workflowdata):
    url_name = urllib.quote(tag_name,"")
    mon_url = '/api/{}/tags/{}/nodes/workflows?name={}'.format(MON_API_VERSION,url_name,workflowname)
    response_tag = fit_common.rackhdapi(mon_url,action='post',payload=workflowdata,rest_headers={"Content-Type": "application/json"})
    return response_tag["status"]

def patch_tag_to_node(nodeid,tagname):
    mon_url = '/api/{}/nodes/{}/tags'.format(MON_API_VERSION,nodeid)
    patchdata = {"tags":[tagname]} 
    response_tag = fit_common.rackhdapi(mon_url,action='patch',payload=patchdata)
    return response_tag["status"]

def get_node_id_list():
    mon_url = '/api/{}/nodes'.format(MON_API_VERSION)    
    response_tag = fit_common.rackhdapi(mon_url)
    catalogs = json.loads(response_tag['text'])
    idfound = []
    for t_nodes in catalogs:
        idfound.append(t_nodes['id'])
    return idfound

def delete_tag_in_node(nodeid,tag_name):
    en_tagname = urllib.quote(tag_name,"")
    mon_url = "/api/{}/nodes/{}/tags/{}".format(MON_API_VERSION,nodeid,en_tagname)
    response_tag = fit_common.rackhdapi(mon_url,action="delete")
    return response_tag["status"]

def get_a_tag_in_node(nodeid,tag_name):
    en_tagname = urllib.quote(tag_name,"")
    mon_url = "/api/{}/nodes/{}/tags/{}".format(MON_API_VERSION,nodeid,en_tagname)
    response_tag = fit_common.rackhdapi(mon_url)
    if response_tag["status"] in range(200,205):
        return response_tag["text"]
    else:
        return response_tag["status"]

# Select nose.plugins.attrib import attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd_api_node_tag_and_label_feature(fit_common.unittest.TestCase):
    def test_api_create_tags_and_check_existing_tags_one_by_one(self):
        self.assertEqual(tesr_down(),0,"clearing the tag environment failed")
        SupportedOperations = ["equals","in","contains","notIn","notContains","greaterThan","lessThan","min","max","regex","notRegex"]
        SupportPlatforms = ["S2600KP","QuantaPlex T41S-2U","D51B-2U (dual 10G LoM)","Dell R630","Dell C6320"]
        print "test operations includes: {}".format(SupportedOperations)
        print "test platforms includes: {}".format(SupportPlatforms)
        for operator in SupportedOperations:
            for platform in SupportPlatforms:
                RandomCharacters = '.'.join(random.sample(string.printable,8))
                Tagname1 = "newtag" + "_" + " " + RandomCharacters + datetime.now().__str__() + " " + RandomCharacters
                if operator in ["in", "notIn"]:
                    NewTag = {"name" :Tagname1,"rules": [{operator:"["+ platform +"]","path": "dmi.System Information.Product Name"}]}
                else:
                    NewTag = {"name" :Tagname1,"rules" :[{operator:platform,"path":"dmi.System Information.Product Name"}]}
                print "create new tag: " + Tagname1
                Str_NewTag = "{\"name\":\"" + Tagname1+"\",\"rules\"+[{\""+operator+"\":\""+platform+"\",\"path\":\"dmi.System Information.Product Name\"}]}"
                mon_url = '/api/{}/tags'.format(MON_API_VERSION)
                mon_data = fit_common.rackhdapi(mon_url,action='post',payload=NewTag)
                self.assertIn(mon_data['status'],range(200,205),"Incorrect HTTP return code: {}".format(mon_data['status']))
                time.sleep(1)
                url_name = urllib.quote(Tagname1,"")
                mon_url = '/api/{}/tags/{}'.format(MON_API_VERSION,url_name)
                mon_data = fit_common.rackhdapi(mon_url)
                self.assertIn(mon_data['status'],range(200,205),"Incorrect HTTP return code: {}".format(mon_data['status']))
                json_tag_data = json.loads(mon_data['text'])
                self.assertTrue(json_tag_data['name'] == NewTag['name'] and json_tag_data['rules']==NewTag['rules'],"tag field error")
                print "query tag: " + Tagname1 + "successfully!"
        print "test: tag creation and query succeed!"
        self.assertEqual(tear_down(),0,"clearing the tag environment failed")
                  
        
    def test_api_create_tags_and_check_tag_list(self):
        self.assertEqual(tear_down(),0,"clearing the tag environment failed")
        SupportedOperations = ["equals","in","contains","notIn","notContains","greaterThan","lessThan","min","max","regex","notRegex"]
        SupportPlatforms = ["S2600KP","QuantaPlex T41S-2U","D51B-2U (dual 10G LoM)","Dell R630","Dell C6320"]
        tag_pool = []
        for operator in SupportedOperations:
            for platform in SupportPlatforms:
                RandomCharacters = ''.join(random.sample(string.letters,8))
                Tagname1 = "newtag" + " "+RandomCharacters
                if operator in ["in", "notIn"]:
                    NewTag = {"name" :Tagname1, "rules" :[{operator:[platform],"path":"dmi.System Information.Product Name"}]}
                elif operator in ["greaterThan","lessThan","max","min"]:
                    NewTag = {"name": Tagname1,"rules" :[{operator:0,"path":"dmi.System Information.Product Name"}]}
                else:
                    NewTag = {"name" :Tagname1,"rules" :[{operator:platform,"path":"dmi.System Information.Product Name"}]}
                response = create_tag(NewTag)
                print "create tag: {}".format(NewTag)
                self.assertIn(response,range(200,205),"Incorret HTTP reponse code:{}".format(response))
                tag_pool.append(NewTag)
        print "created tag lists: {}".format(tag_pool)
        str_taglist = get_tag_list()
        tag_list = json.loads(str_taglist)
        for dictitem in tag_pool:
            item_found_flag = 0
            for tagitem in tag_pool:
                if tagitem["name"] == dictitem["name"]:
                    item_found_flag = 1
                    self.assertEqual(tagitem["rules"],dictitem["rules"],"Fail to compare, item{} is mismatch!".format(tagitem["name"]))
            self.assertNotEqual(item_found_flag,0,"Fail to compare, item{} is mismatch!".format(tagitem["name"]))
        print "test: all tag listing succeed!"
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")

    def test_api_create_tags_and_check_node_list_with_the_given_tag(self):
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")
        SupportPlatforms = {'Rinjin KP':'S2600KP','Quanta T41':'QuantaPlex T41S-2U','Quanta D51':'D51B-2U (dual 10G LoM)'}
        for platform in SupportPlatforms.keys():
            platformname = platform
            NewTag = {"name":platformname,"rules":[{"equals":SupportPlatforms[platform],"path":"dmi.System Information.Product Name"}]}
            response = create_tag(NewTag)
            self.assertIn(response,range(200,205),"Incorrect HTTP response code: {}".format(response))
            time.sleep(5)
            str_tagnodelist = get_node_by_tag(platform)
            node_number = 0
            print "currrent tag name is: {}".format(platformname)
            #read config information from stack 100 config
            for node in fit_common.STACK_CONFIG['100']['nodes']:
                if node['sku']==platformname:
                    node_number = node_number + 1      
            print "the node number  of the sku {} are: {}".format(platformname,node_number)
            if len(str_tagnodelist)==2:
                self.assertEqual(node_number,0,"The nodes search with tag {} been verified".format(platform))
            else:
                tagnodelist = json.loads(str_tagnodelist)
                tagfound = 0
                for t_nodes in tagnodelist:
                    tagfound = tagfound + 1
                print "(test) the node number of the sku are: {}".format(tagfound)
                self.assertEqual(tagfound, node_number,"The nodes serach with tag {} been verified".format(platform))
        print "test node listing with given tag succeed!"
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")

		
    def test_api_post_workflow_to_nodes_with_a_given_tag(self):
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")
        grouptag = {"name":"firstgroup","rules":[{"equals":"For Power Test Only","path":"dmi.system Information.Product Name"}]}
        create_tag(grouptag)
        dict_monorail_nodes = test_api_utils.get_node_list_by_type("compute")
        firstgroup_node = []
        secondgroup_node = []
        ipmiusername = fit_common.GLOBAL_CONFIG['credentials']['bmc'][0]['username']
        ipmipassword = fit_common.GLOBAL_CONFIG['credentials']['bmc'][0]['password']
        i = 0
        for node_id in dict_monorail_nodes:
            if i<5:
                firstgroup_node.append(node_id)
                response = patch_tag_to_node(node_id,"firstgroup")
                self.assertIn(response,range(200,205),"post tag node {} fail".format(node_id))
            else:
                secondgroup_node.append(node_id)
            print fit_common.ARGS_LIST
            str_bmc_ip = test_api_utils.get_compute_bmc_ip(node_id)
            print "the node id: {} ip address: {}".format(node_id,str_bmc_ip)
            if str_bmc_ip != 1 and str_bmc_ip != 2:
                str_cmd = "ipmitool -I lanplus -H {} -U {} -P {} chassis power status{}".format(str_bmc_ip,ipmiusername,ipmipassword,chr(13))
                rsp = fit_common.remote_shell(str_cmd)
                self.assertIn('Chassis Power is on',rsp['stdout'],'Computer node need to start ID:{},command response:{}'.format(node_id,rsp))
            i = i+1
        print "firstgroup: {}\nsecondgroup: {}".format(firstgroup_node,secondgroup_node)
        response = post_workflow_to_nodes_by_tag("firstgroup","Graph.PowerOff.Node",{})
        self.assertIn(response,range(200,205),"POST workflow fails, return code: {}".format(response))
        time.sleep(20)
        print "finish post workflow"
        time.sleep(30)
        for node_id in firstgroup_node:
            str_bmc_ip = test_api_utils.get_compute_bmc_ip(node_id)
            if str_bmc_ip != 1 and str_bmc_ip != 2:
                str_cmd = "ipmitool -I lanplus -H {} -U {} -P {} chassis power status{}".format(str_bmc_ip,ipmiusername,ipmipassword,chr(13))
                rsp = fit_common.remote_shell(str_cmd)
                print "{}".format(rsp['stdout'])
                time.sleep(1)
                self.assertIn('Chassis Power is off',rsp['stdout'],"Computer node {} did not power off!".format(node_id))
        print"firstgroup status: power off\n{}".format(firstgroup_node)
        for node_id in secondgroup_node:
            str_bmc_ip = test_api_utils.get_compute_bmc_ip(node_id)
            if str_bmc_ip != 1 and str_bmc_ip != 2:
                str_cmd = "ipmitool -I lanplus -H {} -U {} -P {} chassis power status{}".format(str_bmc_ip,ipmiusername,ipmipassword,chr(13))
                rsp = fit_common.remote_shell(str_cmd)
                time.sleep(1)
                print "{}".format(rsp['stdout'])
                self.assertIn('Chassis Power is on',rsp['stdout'],"Computer node {} did not power on!".format(node_id))
        print "secondgroup status: power on: {}".format(secondgroup_node)
        print "power on node in firstgroup..."
        post_workflow_to_nodes_by_tag("firstgroup","Graph.PowerOn.Node",{})
        time.sleep(20)
        for node_id in firstgroup_node:
            str_bmc_ip = test_api_utils.get_compute_bmc_ip(node_id)
            if str_bmc_ip != 1 and str_bmc_ip != 2:
                str_cmd = "ipmitool -I lanplus -H {} -U {} -P {} chassis power status{}".format(str_bmc_ip,ipmiusername,ipmipassword,chr(13))
                rsp = fit_common.remote_shell(str_cmd)
                time.sleep(1)
                print "{}".format(rsp['stdout'])
                self.assertIn('Chassis Power is on',rsp['stdout'],"Computer node {} did not power on!".format(node_id))
        print "firstgtoup status: power on!\n{}".format(secondgroup_node)
        print "test: workflow post to nodes with given tag succeeed!"
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")

    def test_api_assgin_tags_to_selected_nodes(self):
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")
        manualtag = {"name":"AssignTest","rules":[{"equals":"Only for assign test","path":"dmi.System Information.Product Name"}]}
        response=create_tag(manualtag)
        self.assertIn(response,range(200,205),"Incorrect HTTP return Code:{}".format(response))
        print "create the AssignTest tag to stack!"
        nodeids_dicovered = get_node_id_list()
        choosen_nodes = random.sample(nodeids_dicovered,3)
        print "the choosen nodes are: {}".format(choosen_nodes)
        for node in choosen_nodes:
            patch_tag_to_node(node,"AssignTest")
        print "patch the Assign tag to the choosen nodes"
        str_tagnodelist = get_node_by_tag("AssignTest")
        self.assertNotEqual(len(str_tagnodelist),2,"Could not find the system with that tag")
        if len(str_tagnodelist)!=2:
            tagnodelist = json.loads(str_tagnodelist)
            id_found_by_tag = []
            for t_nodes in tagnodelist:
                id_found_by_tag.append(t_nodes['id'])
            id_found_by_tag.sort(reverse=True)
            nodeids_dicovered.sort(reverse=True)
            id_found_by_tag.sort()
            choosen_nodes.sort()
            set1 = set(id_found_by_tag)
            set2 = set(choosen_nodes)
            print "the tag found in nodes:{}\nthe choosen nodes are:{}".format(id_found_by_tag,choosen_nodes)
            self.assertEqual(len(list(set1.difference(set2))),0,"Could not find the system with that tag!")
            print "test: manual tag assignment succeed!"
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")
                 
    def test_api_check_tag_list_on_the_node(self):
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")
        keyword_dict = {'QuantaPlex T41S-2U':'dmi.System Information.Product Name'}
        i=0
        tagrecordlist = []
        sku_discovery_list = get_node_list_by_sku('Quanta T41')
        print "the Quanta T41 nodes are :{}".format(sku_discovery_list)
        for i in range(3):
            for keyword in keyword_dict.keys():
                path = keyword_dict[keyword]
                NewTag = {"name":"Autotag_"+str(i),"rules":[{"equals": keyword,"path":path}]}
                response = create_tag(NewTag)
                self.assertIn(response,range(200,205),"Incorrect HTTP response code: {}".format(response))
                tagrecordlist.append("Autotag_"+str(i))
                i = i+1
        for j in range(3):
            manualtagname = "Manualtag_"+str(j)
            manualtag = {"name":manualtagname,"rules":[{"equals":"This is dummy rule","path":"dmi.System Information.Product Name"}]}
            create_tag(manualtag)
            tagrecordlist.append(manualtagname)
            for s_nodes in sku_discovery_list:
                patch_tag_to_node(s_nodes,manualtagname)
        print "the created tag are: {}".format(tagrecordlist)
        time.sleep(10)
        for s_nodes in sku_discovery_list:
            str_taglist = get_tag_list_on_node(s_nodes)
            print "(test) the node {} have  tag list:{}".format(s_nodes,str_taglist)
            tag_list = list(json.loads(str_taglist))
            tag_list.sort()
            tagrecordlist.sort()
            set1 = set(tag_list)
            set2 = set(tagrecordlist)
            self.assertEqual(len(list(set1.difference(set2))),0,"list Node by Tag Test Fail!")  
        print "test: tag listing in one node succeed!"
        self.assertEqual(tear_down(),0,"clearing the test environment failed!")

    def test_api_delete_tags_in_the_ORA(self):
        str_taglist = get_tag_list()
        taglist = json.loads(str_taglist)
        for tagitem in taglist:
            tagname = tagitem["name"]
            delete_response = delete_tag(tagname)
            self.assertIn(delete_response,range(200,205),"Fail to clear up tag-"+tagname)
        str_taglist_after = get_tag_list()
        self.assertLessEqual(len(str_taglist_after),3,"Fail to claer up Tag list"+str_taglist_after)
        print "test: tag delete in stack success!"

    def test_api_delete_tag_from_a_node(self):
        nodes_list = get_node_id_list()
        NewTag = {"name":"only for test1","rules":[{"equals":"test1","path":"dmi.System Information.Product Name"}]}
        create_tag(NewTag)
        for node in nodes_list:
            patch_tag_to_node(node,"only for test1")
        print "patch the tag only for test1 to nodes!"
        for node in nodes_list:
            tags = get_tag_list_on_node(node)
            tag_list = json.loads(tags)
            print "node {} has tag {}".format(node,tag_list)
            for tag in tag_list:
                response = delete_tag_in_node(node,tag)
                self.assertIn(response,range(200,205),"Fail to delete the tag!")
                check_response = get_a_tag_in_node(node,tag)
                self.assertEqual(check_response,404,"Fail to delete the tag!")
            str_taglist_after = get_tag_list_on_node(node)
            self.assertLessEqual(len(str_taglist_after),2,"Fail to clear up Tag on node "+node)
        print "test: tag delete from one node success!"


if __name__ == '__main__':
    fit_common.unittest.main()
