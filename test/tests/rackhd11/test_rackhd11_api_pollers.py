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


# Local methods
MON_NODES = fit_common.node_select()

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class rackhd11_api_pollers(fit_common.unittest.TestCase):
    def test_api_11_pollers(self):
        api_data = fit_common.rackhdapi("/api/1.1/pollers")
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            # check required fields
            self.assertGreater(item['pollInterval'], 0, 'pollInterval field error')
            self.assertGreaterEqual(item['failureCount'], 0, 'failureCount field error')
            for subitem in ['config', 'createdAt', 'node', 'type']:
                if fit_common.VERBOSITY >= 2:
                    print "Checking:", item['id'], subitem
                self.assertGreater(len(item[subitem]), 0, subitem + ' field error')
        # duplicate check
        nodelist = api_data['json']
        for nodenum in range(1, len(api_data['json'])):
            # poller node ID
            for nodecheck in range(0, len(api_data['json'])):
                if nodenum != nodecheck:
                    self.assertNotEqual(nodelist[nodenum]['id'], nodelist[nodecheck]['id'],
                                        "Duplicate poller id " + nodelist[nodenum]['id'])

    def test_api_11_pollers_post_delete(self):
        mon_ip_addr = "172.31.128.200"
        poller_id = fit_common.rackhdapi("/api/1.1/nodes/" + MON_NODES[0])['json']['id']
        data_payload = {"name": "test", "type": "ipmi",
                        "ip": str(mon_ip_addr),
                        "user": "root", "password": "1234567",
                        "node": str(poller_id), "pollInterval": 100,
                        "config":{"command":"sdr"}}

        # Create a new SDR poller, should return status 200
        api_data = fit_common.rackhdapi('/api/1.1/pollers/', action="post",
                                           payload=data_payload)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))


        # Check that the new poller shows up in the GET
        mon_url = "/api/1.1/pollers/" + api_data['json']["id"]
        api_data = fit_common.rackhdapi(mon_url)
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        # Delete the new poller, should return status 204
        api_data = fit_common.rackhdapi(mon_url, action="delete")
        self.assertEqual(api_data['status'], 204, 'Incorrect HTTP return code, expected 204, got:' + str(api_data['status']))

        # Check that the poller can no longer be retrieved (404 Not Found)
        api_data = fit_common.rackhdapi(mon_url)
        self.assertEqual(api_data['status'], 404, 'Incorrect HTTP return code, expected 404, got:' + str(api_data['status']))


        # Negative test:  Try creating an invalid poller with no config block
        # This currently does not work in the Monorail API
        # data_payload = {"name": "test", "type": "ipmi",
        #               "ip": str(mon_ip_addr),
        #                "user": "root", "password": "1234567",
        #                "node": str(MON_NODES[0]["id"]), "pollInterval": 100}
        # api_data = fit_common.rackhdapi('/api/1.1/pollers/', action="post",
        #                                   payload=data_payload)
        # Guessing on the return code, fix this when it works
        #self.assertEqual(api_data['status'], 400, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def test_api_11_pollers_catalog(self):
        # Get poller catalog
        mon_pollers = fit_common.rackhdapi("/api/1.1/pollers")['json']
        # iterate through poller IDs
        for poller_id in mon_pollers:
            # check for up to 120 seconds before giving up (pollers go every 60 seconds)
            max_cycles = 60
            sleep_delay = 2
            for dummy in range(0, max_cycles):
                api_data = fit_common.rackhdapi("/api/1.1/pollers/" + poller_id['id'] +
                                                   "/data")
                if api_data['status'] == 200:
                    break
                fit_common.time.sleep(sleep_delay)
            self.assertEqual(api_data['status'], 200, 'Poller timeout on ID ' + poller_id['id'])
            # check for data in each poller type
            for item in api_data['json']:
                if 'sel' in item:
                    self.assertGreater(len(item['sel']), 0, 'sel' + ' poller data empty')
                if 'sdr' in item:
                    self.assertGreater(len(item['sdr']), 0, 'sdr' + ' poller data empty')

    def test_api_11_pollers_library(self):
        api_data = fit_common.rackhdapi('/api/1.1/pollers/library')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        for item in api_data['json']:
            if fit_common.VERBOSITY >= 2:
                print "Checking:", item['name']
            self.assertGreater(len(item['name']), 0, 'name field error')
            self.assertGreater(len(item['config']), 0, 'config field error')

    def test_api_11_pollers_duplicates(self):
        api_data = fit_common.rackhdapi('/api/1.1/pollers/library')
        for item in api_data['json']:
            poll_data = fit_common.rackhdapi('/api/1.1/pollers/library/' + item['name'])
            self.assertEqual(poll_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
            self.assertGreater(len(item['name']), 0, 'name field error')
            self.assertGreater(len(item['config']), 0, 'config field error')
        # duplicate check
        nodelist = api_data['json']
        for nodenum in range(1, len(api_data['json'])):
            # poller library name
            for nodecheck in range(0, len(api_data['json'])):
                if nodenum != nodecheck:
                    self.assertNotEqual(nodelist[nodenum]['name'], nodelist[nodecheck]['name'],
                                        "Duplicate poller lib name " + nodelist[nodenum]['name'])

if __name__ == '__main__':
    fit_common.unittest.main()
