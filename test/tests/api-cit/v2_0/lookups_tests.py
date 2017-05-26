'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


@attr(regression=False, smoke=True, lookups_api2_tests=True)
class LookupsTests(fit_common.unittest.TestCase):

    # Tests within this script use the same created lookup id for testing
    # if updated within a test, use self.__class__.var
    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.lookup = {
            "ipAddress": "11.11.11.11",
            "macAddress": "ae:aa:aa:aa:aa:aa",
            "node": "456"
        }
        cls.lookup_id = ""
        cls.patchedNode = {"node": "666"}

    def test_check_lookups(self):
        # """ Testing GET:/lookups """
        Api().lookups_get()
        rsp = self.__client.last_response
        # logs.debug("Lookup list: %s", dumps(rsp.data, indent=4))
        self.assertEqual(200, rsp.status, msg=rsp.reason)
        self.assertNotEqual(0, len(rsp.data))

    def test_check_lookups_query(self):
        # """ Testing GET:/lookups?q=term """
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        self.assertNotEqual(0, len(nodes), msg='Node list was empty!')
        Api().obms_get()
        obms = loads(self.__client.last_response.data)
        logs.debug("OBM get data: %s", dumps(obms, indent=4))
        hosts = []
        for o in obms:
            hosts.append(o.get('config').get('host'))
        self.assertNotEqual(0, len(hosts), msg='No OBM hosts were found!')
        logs.debug("Hosts: %s", dumps(hosts, indent=4))
        for host in hosts:
            logs.debug("Looking up host: %s", host)
            Api().lookups_get(q=host)
            rsp = self.__client.last_response
            self.assertEqual(200, rsp.status, msg=rsp.reason)
            self.assertNotEqual(0, len(rsp.data))

    @depends(after='test_check_lookups_query')
    def test_check_lookup_id(self):
        # """ Testing GET:/lookups/:id """
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        self.assertNotEqual(0, len(nodes), msg='Node list was empty!')
        Api().obms_get()
        obms = loads(self.__client.last_response.data)
        self.assertNotEqual(0, len(obms), msg='No OBM settings found!')
        entries = []
        for obm in obms:
            host = obm.get('config').get('host')
            Api().lookups_get(q=host)
            hlist = loads(self.__client.last_response.data)
            entries.append(hlist)

        self.assertNotEqual(0, len(entries), msg='No lookup entries found!')
        for entry in entries:
            for id in entry:
                Api().lookups_get_by_id(id.get('id'))
                rsp = self.__client.last_response
                self.assertEqual(200, rsp.status, msg=rsp.reason)

    @depends(after='test_check_lookup_id')
    def test_post_lookup(self):
        # """ Testing POST /"""

        # Validate that the lookup has not been posted from a previous test
        Api().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        for i, val in enumerate(rsp):
            if self.lookup.get("macAddress") == str(rsp[i].get('macAddress')):
                    deleteID = str(rsp[i].get('id'))
                    logs.info(" Deleting the lookup with the same info before we post again, ID: %s", deleteID)
                    Api().lookups_del_by_id(deleteID)

        # Add a lookup
        Api().lookups_post(self.lookup)
        rsp = self.__client.last_response
        self.assertEqual(201, rsp.status, msg=rsp.reason)
        self.lookup_id = str(loads(rsp.data).get('id'))
        logs.debug("ID is %s", self.lookup_id)

        # other tests depend on the value
        self.__class__.lookup_id = self.lookup_id
        logs.info(" The lookup ID from post: %s", self.lookup_id)

        # Validate the content
        Api().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        self.assertEqual(str(rsp[0].get("ipAddress")), str(self.lookup.get("ipAddress")))
        self.assertEqual(str(rsp[0].get("macAddress")), str(self.lookup.get("macAddress")))
        self.assertEqual(str(rsp[0].get("node")), str(self.lookup.get("node")))

    @depends(after='test_post_lookup')
    def test_post_lookup_negativeTesting(self):
        # """ Negative Testing POST / """
        # Validate that a POST for a lookup with same id as an existing one gets rejected
        logs.info(" The lookup ID to be re-posted is %s", self.lookup_id)
        try:
            Api().lookups_post(self.lookup)
        except ApiException as e:
            self.assertEqual(400, e.status, msg='Expected 400 status, received {}'.format(e.status))
        except (TypeError, ValueError) as e:
            assert(e.message)

    @depends(after='test_post_lookup')
    def test_patch_lookup(self):
        # """ Testing PATCH /:id"""
        logs.info(" The lookup ID to be patched is %s", self.lookup_id)
        Api().lookups_patch_by_id(self.lookup_id, self.patchedNode)

        # validate that the node element has been updated
        Api().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        self.assertEqual(str(rsp[0].get("node")), self.patchedNode.get("node"))

    @depends(after='test_patch_lookup')
    def test_delete_lookup(self):
        # """ Testing DELETE /:id """
        # Validate that the lookup is there before it is deleted
        Api().lookups_get_by_id(self.lookup_id)
        rsp = self.__client.last_response
        self.assertEqual(200, rsp.status, msg=rsp.reason)

        # delete the lookup
        logs.info(" The lookup ID to be deleted is %s", self.lookup_id)
        Api().lookups_del_by_id(self.lookup_id)
        rsp = self.__client.last_response
        self.assertEqual(204, rsp.status, msg=rsp.reason)

        # Validate that the lookup has been deleted and the returned value is an empty list
        try:
            Api().lookups_get_by_id(self.lookup_id)
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))
        except (TypeError, ValueError) as e:
            assert(e.message)
