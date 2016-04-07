from config.api2_0_config import *
from on_http_api2_0 import ApiApi as WorkflowApi
from on_http_api2_0 import rest
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import * 
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads
import json

LOG = Log(__name__)

@test(groups=['workflowTasks_api2.tests'])
class WorkflowTasksTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__workflows = None
        self.workflowTaskDict ={
            "friendlyName": "fn_1",
            "injectableName": "in_1",
            "implementsTask": "im_1",
            "options": {},
            "properties": {}
        }

    @test(groups=['workflowTasks_api2.tests', 'api2_workflowTasks_get'])
    def test_workflowTasks__get(self):
        """ Testing GET:/worflows/tasks"""
        WorkflowApi().workflows_get_all_tasks()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)), message='Workflow tasks list was empty!')

    @test(groups=['workflowTasks_library_put'], depends_on_groups=['workflowTasks_library_get'])
    def test_workflowTasks_put(self):
        """ Testing PUT:/workflowTasks """
        #Get the number of workflowTasks before we add one
        WorkflowApi().workflows_get_all_tasks()
        workflowTasksBefore = len(json.loads(self.__client.last_response.data))

        #Making sure that there is no workflowTask with the same name from previous test runs
        rawj=  json.loads(self.__client.last_response.data)
        listLen =len(json.loads(self.__client.last_response.data))
        inList = False
        for i, val in enumerate (rawj):
            if ( self.workflowTaskDict['friendlyName'] ==  str (rawj[i].get('friendlyName')) or inList ):
                inList = True
                fnameList = str (rawj[i].get('friendlyName')).split('_')
                if len(fnameList) > 1:
                    suffix= int (fnameList[1]) + 1
                    self.workflowTaskDict['friendlyName']= fnameList[0]+ '_' + str(suffix)
                    inameList = str (rawj[i].get('injectableName')).split('_')
                    self.workflowTaskDict['injectableName']= inameList[0]+ '_' + str(suffix)

        #adding a workflow task
        LOG.info ("Adding workflow task : " +  str(self.workflowTaskDict))
        WorkflowApi().workflows_put_task(body=self.workflowTaskDict)
        resp= self.__client.last_response
        assert_equal(201,resp.status)

        #Getting the number of profiles after we added one
        WorkflowApi().workflows_get_all_tasks()
        workflowTasksAfter = len(json.loads(self.__client.last_response.data))
        resp= self.__client.last_response
        assert_equal(200,resp.status, message=resp.reason)

        #Validating that the profile has been added
        assert_equal(workflowTasksAfter,workflowTasksBefore+1)

        #Validating the content is as expected
        rawj=  json.loads(self.__client.last_response.data)
        listLen =len(json.loads(self.__client.last_response.data))
        readWorkflowTask= rawj[len(rawj)-1]
        readFriendlyName= readWorkflowTask.get('friendlyName')
        readInjectableName  = readWorkflowTask.get('injectableName')
        assert_equal(readFriendlyName,self.workflowTaskDict.get('friendlyName'))
        assert_equal(readInjectableName,self.workflowTaskDict.get('injectableName'))
