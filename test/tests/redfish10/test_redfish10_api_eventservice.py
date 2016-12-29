'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)

class redfish10_api_eventservice(fit_common.unittest.TestCase):
    def test_redfish_v1_eventservice(self):
        api_data = fit_common.rackhdapi('/redfish/v1/EventService')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))

    def test_redfish_v1_eventservice_subscriptions(self):
        api_data = fit_common.rackhdapi('/redfish/v1/EventService/Subscriptions')
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        # iterate through links
        for item in api_data['json']['Members']:
            self.assertEqual(fit_common.rackhdapi(item['@odata.id'])['status'], 200, "Bad or missing link: " + item['@odata.id'])

    def test_redfish_v1_eventservice_subscriptions_post_get_delete(self):
        payload = {
                  "@odata.context": "string",
                  "@odata.id": str(fit_common.time.time()),
                  "@odata.type": str(fit_common.time.time()),
                  "Context": "Test",
                  "Description": str(fit_common.time.time()),
                  "Destination": str(fit_common.time.time()),
                  "EventTypes": [
                    "StatusChange"
                  ],
                  "HttpHeaders": [
                    {}
                  ],
                  "Id": str(fit_common.time.time()),
                  "Name": str(fit_common.time.time()),
                  "Oem": {},
                  "Protocol": "Redfish"
                }
        api_data = fit_common.rackhdapi('/redfish/v1/EventService/Subscriptions', action="post", payload=payload)
        self.assertEqual(api_data['status'], 201, "Was expecting code 201. Got " + str(api_data['status']))
        api_data = fit_common.rackhdapi('/redfish/v1/EventService/Subscriptions/' + api_data['json']['Id'])
        self.assertEqual(api_data['status'], 200, "Was expecting code 200. Got " + str(api_data['status']))
        api_data = fit_common.rackhdapi('/redfish/v1/EventService/Subscriptions/' + api_data['json']['Id'], action="delete")
        self.assertEqual(api_data['status'], 204, "Was expecting code 204. Got " + str(api_data['status']))

    def test_redfish_v1_eventservice_actions_submittestevent_post(self):
        payload = {}
        api_data = fit_common.rackhdapi('/redfish/v1/EventService/Actions/EventService.SubmitTestEvent', action="post", payload=payload)
        self.assertEqual(api_data['status'], 202, "Was expecting code 202. Got " + str(api_data['status']))

if __name__ == '__main__':
    fit_common.unittest.main()
