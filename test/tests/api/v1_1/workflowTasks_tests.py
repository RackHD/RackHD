
import json
from config.api1_1_config import *
from on_http import WorkflowTasksApi as WorkflowTasks
from on_http import rest
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)



@test(groups=['workflowTasks.tests'])
class WorkflowTasksTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.workflowTaskDict ={
            "friendlyName": "fn_1",
            "injectableName": "in_1",
            "implementsTask": "im_1",
            "options": {},
            "properties": {}
        }


    @test(groups=['workflowTasks.tests', 'workflowTasks_library_get'])
    def test_workflowTasks_library_get(self):
        """ Testing GET:/tasks/library"""
        WorkflowTasks().api1_1_workflows_tasks_library_get()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)), message='Workflow tasks list was empty!')


    @test(groups=['workflowTasks_library_put'], depends_on_groups=['workflowTasks_library_get'])
    def test_workflowTasks_put(self):
        """ Testing PUT:/workflowTasks """
        #Get the number of workflowTasks before we add one
        WorkflowTasks().api1_1_workflows_tasks_library_get()
        workflowTasksBefore = len(json.loads(self.__client.last_response.data))

        #Making sure that there is no workflowTask with the same name from previous test runs
        rawj=  json.loads(self.__client.last_response.data)
        listLen =len(json.loads(self.__client.last_response.data))
        inList = False
        for i, val in enumerate (rawj):
            if ( self.workflowTaskDict['friendlyName'] ==  str (rawj[i].get('friendlyName')) or inList ):
                inList = True
                fnameList = str (rawj[i].get('friendlyName')).split('_')
                suffix= int (fnameList[1]) + 1
                self.workflowTaskDict['friendlyName']= fnameList[0]+ '_' + str(suffix)
                inameList = str (rawj[i].get('injectableName')).split('_')
                self.workflowTaskDict['injectableName']= inameList[0]+ '_' + str(suffix)

        #adding a workflow task
        LOG.info ("Adding workflow task : " +  str(self.workflowTaskDict))
        WorkflowTasks().api1_1_workflows_tasks_put(body=self.workflowTaskDict)
        resp= self.__client.last_response
        assert_equal(200,resp.status)

        #Getting the number of profiles after we added one
        WorkflowTasks().api1_1_workflows_tasks_library_get()
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






