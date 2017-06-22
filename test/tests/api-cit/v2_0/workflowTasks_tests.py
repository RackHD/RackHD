'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as WorkflowApi
from json import loads
from nose.plugins.attrib import attr
from nosedep import depends

logs = flogging.get_loggers()


@attr(regression=False, smoke=True, workflows_tasks_api2_tests=True)
class WorkflowTasksTests(fit_common.unittest.TestCase):

    def setUp(self):
        self.__client = config.api_client
        self.__workflows = None
        self.workflowTaskDict = {
            "friendlyName": "fn_1",
            "injectableName": "in_1",
            "implementsTask": "im_1",
            "options": {},
            "properties": {}
        }

    def test_workflowTasks__get(self):
        # """ Testing GET:/worflows/tasks"""
        WorkflowApi().workflows_get_all_tasks()
        self.assertEqual(200, self.__client.last_response.status)
        self.assertNotEqual(0, len(loads(self.__client.last_response.data)), msg='Workflow tasks list was empty!')

    @depends(after='test_workflowTasks__get')
    def test_workflowTasks_put(self):
        # """ Testing PUT:/workflowTasks """
        # Get the number of workflowTasks before we add one
        WorkflowApi().workflows_get_all_tasks()
        workflowTasksBefore = len(loads(self.__client.last_response.data))

        # Making sure that there is no workflowTask with the same name from previous test runs
        rawj = loads(self.__client.last_response.data)
        inList = False
        for i, val in enumerate(rawj):
            if self.workflowTaskDict['friendlyName'] == str(rawj[i].get('friendlyName')) or inList:
                inList = True
                fnameList = str(rawj[i].get('friendlyName')).split('_')
                if len(fnameList) > 1:
                    suffix = int(fnameList[1]) + 1
                    self.workflowTaskDict['friendlyName'] = fnameList[0] + '_' + str(suffix)
                    inameList = str(rawj[i].get('injectableName')).split('_')
                    self.workflowTaskDict['injectableName'] = inameList[0] + '_' + str(suffix)

        # adding a workflow task
        logs.info("Adding workflow task : " + str(self.workflowTaskDict))
        WorkflowApi().workflows_put_task(body=self.workflowTaskDict)
        resp = self.__client.last_response
        self.assertEqual(201, resp.status)

        # Getting the number of profiles after we added one
        WorkflowApi().workflows_get_all_tasks()
        workflowTasksAfter = len(loads(self.__client.last_response.data))
        resp = self.__client.last_response
        self.assertEqual(200, resp.status, msg=resp.reason)

        # Validating that the profile has been added
        self.assertEqual(workflowTasksAfter, workflowTasksBefore + 1)

        # Validating the content is as expected
        rawj = loads(self.__client.last_response.data)
        readWorkflowTask = rawj[len(rawj) - 1]
        readFriendlyName = readWorkflowTask.get('friendlyName')
        readInjectableName = readWorkflowTask.get('injectableName')
        self.assertEqual(readFriendlyName, self.workflowTaskDict.get('friendlyName'))
        self.assertEqual(readInjectableName, self.workflowTaskDict.get('injectableName'))
