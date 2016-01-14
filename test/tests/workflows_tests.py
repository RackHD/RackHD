
import json
from config.settings import *
from on_http import WorkflowsApi as Workflows
from on_http import NodesApi as Nodes
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
import time


LOG = Log(__name__)

@test(groups=['workflows.tests'])
class WorkflowsTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.workflowDict = {
                                "friendlyName": "Shell Commands Hwtest_1",
                               "injectableName": "Graph.post.test",
                                "tasks": [{"taskName": "Task.Trigger.Send.Finish"}]
                            }

    @test(groups=['workflows.tests', 'workflows_get'])
    def test_workflows_get(self):
        """ Testing GET:/"""
        Workflows().api1_1_workflows_get()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)), message='Active workflows list was empty!')

    @test(groups=['workflows_get_id'],depends_on_groups=['workflows_get'])
    def test_workflows_id_get(self):
        """ Testing GET:/identifier"""
        # Getting the identifier of the first workflow in order to validate the get-id function
        Workflows().api1_1_workflows_get()
        rawj=  json.loads(self.__client.last_response.data)
        identifier=rawj[0].get("id")
        Workflows().api1_1_workflows_identifier_get(identifier)
        assert_equal(200,self.__client.last_response.status)

    @test(groups=['workflows_get_id'],depends_on_groups=['workflows_get'])
    def test_negative_workflows_id_get(self):
        """ Negative Testing GET:/identifier"""
        try:
            Workflows().api1_1_workflows_identifier_get("WrongIdentifier")
        except Exception,e:
            assert_equal(404,e.status, message = 'status should be 404')

    @test(groups=['workflows.tests', 'workflows_library_get'])
    def test_workflows_library_get(self):
        """ Testing GET:/library"""
        Workflows().api1_1_workflows_library_get()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)), message='Active workflows list was empty!')

    @test(groups=['workflows_put'], depends_on_groups=['workflows_library_get'])
    def test_workflows_put(self):
        """ Testing PUT:/workflows:/library """

        #Making sure that there is no workflowTask with the same name from previous test runs
        Workflows().api1_1_workflows_library_get()
        rawj =  json.loads(self.__client.last_response.data)
        listLen =len(rawj)
        workflowIndex = 0

        for i, val in enumerate (rawj):
            if ( self.workflowDict['injectableName'] ==  str (rawj[i].get('injectableName')) ):
                fnameList = str (rawj[i].get('friendlyName')).split('_')
                suffix= int (fnameList[1]) + 1
                self.workflowDict['friendlyName']= fnameList[0]+ '_' + str(suffix)
                workflowIndex = i
                break

        #adding/updating  a workflow task
        LOG.info ("Adding workflow task : " +  str(self.workflowDict))
        Workflows().api1_1_workflows_put(body=self.workflowDict)
        resp= self.__client.last_response
        assert_equal(200,resp.status)

        #Validating the content is as expected
        Workflows().api1_1_workflows_library_get()
        rawj=  json.loads(self.__client.last_response.data)
        listLen =len(json.loads(self.__client.last_response.data))
        readWorkflowTask= rawj[workflowIndex]
        readFriendlyName= readWorkflowTask.get('friendlyName')
        readInjectableName  = readWorkflowTask.get('injectableName')
        assert_equal(readFriendlyName,self.workflowDict.get('friendlyName'))
        assert_equal(readInjectableName,self.workflowDict.get('injectableName'))

    @test(groups=['workflows_library_identifier_get'], depends_on_groups=['workflows_put'])
    def test_workflows_library_identifier_get(self):
        """ Testing GET:/library:/identifier"""
        Workflows().api1_1_workflows_library_identifier_get(self.workflowDict.get('injectableName'))
        assert_equal(200,self.__client.last_response.status)
        assert_equal(self.workflowDict.get('friendlyName'),str(json.loads(self.__client.last_response.data)[0].get('friendlyName')))

    @test(groups=['workflows_library_identifier_get', 'test_node_workflows_post'],depends_on_groups=['workflows_put'])
    def test_node_workflows_post(self):
        """Testing node POST:id/workflows"""
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)

        for n in nodes:
            if n.get('type') == 'compute':
                Nodes().api1_1_nodes_identifier_workflows_post(n.get('id'),name='Graph.noop-example',body={})
                returnedWorkflowID=str(json.loads(self.__client.last_response.data).get("id"))

                #wait for the workflow to finsih
                sleepTimeIncrement = 1
                waitedtime =0
                timeOut = 16
                i =0
                for  i in range (timeOut) :
                    time.sleep(sleepTimeIncrement)
                    Workflows().api1_1_workflows_identifier_get(returnedWorkflowID)
                    postedWorkflow=  json.loads(self.__client.last_response.data)
                    status= postedWorkflow.get("_status")
                    LOG.info('Attempting to check the status of the posted workflow after {0} sec(s)'.format(i))
                    if  status != "valid":
                        break
                    if status is "valid":
                        waitedtime =  waitedtime + sleepTimeIncrement
                    if i==(timeOut-1):
                        LOG.info ("Timed out after :"+ str(i))

                assert_equal(status,"succeeded")

