'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Verify that a workflow is run when posting a Redfish SimpleUpdate
'''

import fit_path  # NOQA: unused import
import fit_common

NODECATALOG = fit_common.node_select()


# Select test group here using @attr
from nose.plugins.attrib import attr


@attr(all=True, regression=True, smoke=True)
class redfish10_api_updateservice(fit_common.unittest.TestCase):
    def test_redfish_v1_updateservice_actions_updateservicesimpleupdate_post(self):
        nodeid = NODECATALOG[0]
        fit_common.cancel_active_workflows(nodeid)
        on_payload = {"ImageURI": "/dummy.exe", "Targets": [nodeid]}
        api_data = fit_common.rackhdapi('/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate',
                                        action='post', payload=on_payload)
        self.assertEqual(api_data['status'], 201,
                         'Incorrect HTTP return code, expected 201, got:' + str(api_data['status']))
        task_data = fit_common.rackhdapi(api_data['json']['@odata.id'])
        self.assertEqual(task_data['status'], 200, "No task ID found ")
        task_state = task_data['json']['TaskState']
        self.assertIn(task_state, ["Running", "Pending", "Completed", "Exception"],
                      "Bad task state for node:" + nodeid + " state:" + task_state)


if __name__ == '__main__':
    fit_common.unittest.main()
