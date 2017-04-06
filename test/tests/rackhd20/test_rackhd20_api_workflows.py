'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import fit_common
from time import sleep


# Local methods
NODECATALOG = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd20_api_workflows(fit_common.unittest.TestCase):
    def test_api_20_workflows(self):
        api_data = fit_common.rackhdapi("/api/2.0/workflows")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            # check required fields
            for subitem in ["id", "name","injectableName", "instanceId", "tasks"]:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['name'], subitem
                self.assertIn(subitem, item, subitem + ' field error')

    def test_api_20_workflows_tasks(self):
        data_payload = {
            "friendlyName": "Shell commands hwtest",
            "injectableName": "Task.Linux.Commands.Hwtest",
            "implementsTask": "Task.Base.Linux.Commands",
            "options": {
                "commands": [
                    {"command": "sudo /opt/test/hwtest",
                     "format": "json", "source": "hwtest"}
                ]
            },
            "properties": {"type": "hwtestRun"}
        }
        api_data = fit_common.rackhdapi("/api/2.0/workflows/tasks", action="put", payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))

    def test_api_20_workflows_put_ipmi(self):
        data_payload = \
            {
                "friendlyName": "TestIPMI",
                "injectableName": 'Graph.Obm.Ipmi.CreateSettings.Test',
                "options": {
                    "obm-ipmi-task":{
                        "user": "rackhd",
                        "password": "rackhd"
                    }
                },
                "tasks": [
                    {
                        "label": "obm-ipmi-task",
                        "taskName": "Task.Obm.Ipmi.CreateSettings"
                    }
            ]
        }
        api_data = fit_common.rackhdapi("/api/2.0/workflows/graphs", action="put", payload=data_payload)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/2.0/workflows/graphs/" + 'Graph.Obm.Ipmi.CreateSettings.Test')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_api_20_workflows_waitOn_anyOf(self):
        data_payload = {
            "friendlyName": "Multi-REST-call",
            "injectableName": "Graph.REST.call",
            "tasks": [
                {
                    "label": "REST-call-good",
                    "taskDefinition": {
                        "friendlyName": "good REST call",
                        "injectableName": "Task.Rest.GET",
                        "implementsTask": "Task.Base.Rest",
                        "options": {
                            "url": "http://localhost:8080/api/1.1/nodes",
                            "method": "GET"
                        },
                        "properties": {}       
                    }
                },
                {
                    "label": "REST-call-2",
                    "taskDefinition": {
                        "friendlyName": "2nd REST call",
                        "injectableName": "Task.Rest.GET",
                        "implementsTask":  "Task.Base.Rest",
                        "options": {
                            "url": "http://localhost:8080/api/1.1/nodes",
                            "method": "GET"
                            },
                        "properties": {}
                    }       
                },
                {
                    "label": "REST-call-bad",
                    "taskDefinition": {
                        "friendlyName": "bad REST call",
                        "injectableName": "Task.Rest.GET",
                        "implementsTask": "Task.Base.Rest",
                        "options": {
                            "url": "http://localhost:8080/api/never/happen",
                            "method": "GET"
                        },
                        "properties": {}
                    }       
                },
                {
                    "label" : "REST-call-final-good",
                    "taskDefinition": {
                        "friendlyName": "final REST call",
                        "injectableName": "Task.Rest.GET",
                        "implementsTask": "Task.Base.Rest",
                        "options": {
                            "url": "http://localhost:8080/api/1.1/nodes",
                            "method": "GET"
                        },
                        "properties": {}
                    },
                    "waitOn":{
                        "anyOf":{
                            "REST-call-good": "succeeded",
                            "REST-call-bad": "succeeded"
                        },
                        "REST-call-2": "succeeded"
                    }
                },
                {
                    "label" : "REST-call-final-pending",
                    "taskDefinition": {
                        "friendlyName": "final REST call",
                        "injectableName":"Task.Rest.GET",
                        "implementsTask": "Task.Base.Rest",
                        "options": {
                            "url": "http://localhost:8080/api/1.1/nodes",
                            "method": "GET"
                        },
                        "properties": {}
                    },
                    "waitOn": {
                        "anyOf":{
                            "REST-call-good": "failed",
                            "REST-call-bad": "failed"
                        }
                    }
                },
                {
                    "label" : "REST-call-final-succeeded-2",
                    "taskDefinition": {
                        "friendlyName": "final REST call",
                        "injectableName": "Task.Rest.GET",
                        "implementsTask": "Task.Base.Rest",
                        "options": {
                            "url": "http://localhost:8080/api/1.1/nodes",
                            "method": "GET"
                        },
                        "properties": {}
                    },
                    "waitOn": {
                        "anyOf": {
                            "REST-call-good": "failed",
                            "REST-call-bad": "succeeded"
                        }
                    }
                }
            ]
        } 
        
        node_id = fit_common.node_select()
        if not node_id:
            print "Cannot find any NODE connected with this RackHD server"
            raise
 
        # Assume previous test will make sure this will success
        setup_return = fit_common.rackhdapi("/api/2.0/workflows/graphs", action="put", payload=data_payload)
        
        graph_query = {}
        graph_query["name"] = data_payload["injectableName"]
        run_return = fit_common.rackhdapi("/api/2.0/nodes/{0}/workflows".format(node_id[0]), action="post", payload=graph_query)
        graph_id = run_return['json']['instanceId']
        
        sleep(5) # Need some time to make sure the workflow is executed successfully
        
        result_return = fit_common.rackhdapi("/api/2.0/workflows/{0}".format(graph_id), action="get")
        running_result = result_return['json']['tasks']
        for task in running_result:
            if task['label'] == "REST-call-final-pending":
                self.assertEqual(task['state'], 'pending', 
                        "When all the conditions under anyOf are failed," +
                        " task should be marked unreachable, but got "+task['state'])

            if task['label'] == "REST-call-final-succeeded-2":
                self.assertEqual(task['state'], 'succeeded', 
                        "When one of the conditions under anyOf is failed but other fufilled," +
                        " task should be reachable and executed, but got "+ task['state'])

            if task['label'] == "REST-call-final-good":
                self.assertEqual(task['state'], 'succeeded', 
                        "When all of the conditions under anyOf is fulfilled," +
                        " task should be reachable and executed, but got " + task['state'])

if __name__ == '__main__':
    fit_common.unittest.main()
