'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
import fit_path
import fit_common


# Local methods
MON_NODES = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd11_api_workflows(fit_common.unittest.TestCase):
    def test_api_11_workflows(self):
        api_data = fit_common.rackhdapi("/api/1.1/workflows")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            # check required fields
            for subitem in ['id', 'name', 'updatedAt', 'createdAt']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['name'], subitem
                self.assertGreater(len(item[subitem]), 0, subitem + ' field error')

    def test_api_11_workflows_tasks(self):
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
        api_data = fit_common.rackhdapi("/api/1.1/workflows/tasks", action="put",
                                           payload=data_payload)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_api_11_workflows_tasks_library(self):
        api_data = fit_common.rackhdapi("/api/1.1/workflows/tasks/library")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item["friendlyName"]
            self.assertGreater(len(item['injectableName']), 0, 'injectableName field error')
            self.assertGreater(len(item['friendlyName']), 0, 'friendlyName field error')

    def test_api_11_workflows_tasks_library_ID(self):
        api_data = fit_common.rackhdapi("/api/1.1/workflows/library/*")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item["friendlyName"]
            self.assertGreater(len(item['injectableName']), 0, 'injectableName field error')
            self.assertGreater(len(item['friendlyName']), 0, 'friendlyName field error')
            self.assertGreater(len(item['tasks']), 0, 'tasks field error')

    def test_api_11_workflows_put_ipmi(self):
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
        api_data = fit_common.rackhdapi("/api/1.1/workflows", action="put", payload=data_payload)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        api_data = fit_common.rackhdapi("/api/1.1/workflows/library/" + 'Graph.Obm.Ipmi.CreateSettings.Test')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
