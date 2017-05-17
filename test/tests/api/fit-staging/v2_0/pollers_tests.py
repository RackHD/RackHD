'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging

from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from json import loads
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['pollers_api2.tests'])
@attr(regression=False, smoke=True, pollers_api2_tests=True)
class PollersTests(fit_common.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.pollers = []
        cls.poller_libs = []
        cls.created_pollers = []

    # @test(groups=['pollers_api2.tests', 'api2_get_pollers_library'])
    def test_get_pollers_lib(self):
        # """Test GET:api/2.0/pollers/library"""
        Api().pollers_lib_get()
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)

        self.assertEqual(200, result.status, msg=result.reason)

        names = [lib['name'] for lib in data]
        self.assertTrue('ipmi' in names and 'snmp' in names, names)

        for lib in data:
            self.assertTrue('config' in lib.keys())

        self.__class__.poller_libs = data

    # @test(groups=['pollers_api2.tests', 'api2_get_pollers_library_by_id'],
    #      depends_on_groups=['api2_get_pollers_library'])
    @depends(after='test_get_pollers_lib')
    def test_get_pollers_lib_by_id(self):
        # """Test GET:api/2.0/pollers/library/:identifier"""
        for lib in self.__class__.poller_libs:
            Api().pollers_lib_by_id_get(identifier=lib['name'])
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)

            self.assertEqual(200, result.status, msg=result.reason)
            self.assertEqual(lib, data)

        try:
            Api().pollers_lib_by_id_get(identifier='not_a_real_poller')
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))

    # @test(groups=['pollers_api2.tests', 'api2_get_pollers'])
    # no dependencies
    def test_get_pollers(self):
        # """Test GET:api/2.0/pollers"""
        Api().pollers_get()
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)

        self.assertEqual(200, result.status, msg=result.reason)
        for poller in data:
            keys = poller.keys()
            self.assertTrue('config' in keys)
            self.assertTrue('type' in keys)
            self.assertTrue('pollInterval' in keys)

        self.__class__.pollers = data

    # @test(groups=['pollers_api2.tests', 'api2_get_pollers_by_id'],
    #      depends_on_groups=['api2_get_pollers'])
    @depends(after='test_get_pollers')
    def test_get_pollers_by_id(self):
        # """Test GET:api/2.0/pollers/:identifier"""
        for poller in self.__class__.pollers:
            Api().pollers_id_get(identifier=poller['id'])
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)

            self.assertEqual(200, result.status, msg=result.reason)
            for key in ['pollInterval', 'paused', 'type', 'config']:
                self.assertEqual(data[key], poller[key])
        try:
            Api().pollers_id_get(identifier='does_not_exist')
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))

    # @test(groups=['pollers_api2.tests', 'api2_create_pollers'])
    # no depends
    def test_create_pollers(self):
        # """Test POST:api/2.0/pollers"""
        pollers = [
            {
                "type": "ipmi",
                "pollInterval": 10000,
                "config": {
                    "command": "sdr",
                    "user": "admin",
                    "password": "admin"
                },
                "paused": True
            },
            {
                "type": "snmp",
                "pollInterval": 10000,
                "config": {
                    "oids": [
                        "IF-MIB::ifSpeed",
                        "IF-MIB::ifOperStatus"
                    ]
                },
                "paused": True
            }
        ]

        self.__class__.created_pollers = []
        for poller in pollers:
            Api().pollers_post(poller)
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)
            poller['config'].pop('password', None)

            self.assertEqual(201, result.status, msg=result.reason)
            for key in poller.keys():
                self.assertEqual(poller[key], data[key])

            self.__class__.created_pollers.append(data)

    # @test(groups=['pollers_api2.tests', 'api2_patch_pollers'],
    #      depends_on_groups=['api2_create_pollers'])
    @depends(after='test_create_pollers')
    def test_pollers_patch(self):
        # """Test PATCH:api/2.0/pollers/:identifier"""
        patch_data = {
            "pollInterval": 5000
        }
        for poller in self.__class__.created_pollers:
            Api().pollers_patch(poller['id'], patch_data)
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)

            self.assertEqual(200, result.status, msg=result.reason)
            self.assertEqual(5000, data['pollInterval'])
            poller = data

        try:
            Api().pollers_patch('does_not_exist', {})
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))

    # @test(groups=['pollers_api2.tests', 'api2_data_get_pollers'],
    #      depends_on_groups=['api2_get_pollers', 'api2_patch_pollers'])
    @depends(after=['test_get_pollers', 'test_pollers_patch'])
    def test_pollers_data_get(self):
        # """Test GET:/api/2.0/pollers/:identifier/data"""
        all_pollers = self.__class__.pollers + self.__class__.created_pollers
        for poller in all_pollers:
            Api().pollers_data_get(poller['id'])
            result = self.__client.last_response
            self.assertTrue(result.status == 200 or result.status == 204, msg=result.reason)
            if result.status == 200:
                self.assertTrue(len(result.data) > 0, 'Poller data length should be non-zero')
            else:
                self.assertEqual(len(result.data), 0, 'Poller data should have 0 length')

    # @test(groups=['pollers_api2.tests', 'api2_current_data_get_pollers'],
    #      depends_on_groups=['api2_get_pollers', 'api2_data_get_pollers'])
    @depends(after='test_pollers_data_get')
    def test_pollers_current_data_get(self):
        # """Test GET:/api/2.0/pollers/:identifier/data/current"""
        all_pollers = self.__class__.pollers + self.__class__.created_pollers
        for poller in all_pollers:
            Api().pollers_data_get(poller['id'])
            result = self.__client.last_response
            self.assertTrue(result.status == 200 or result.status == 204, msg=result.reason)
            if result.status == 200:
                self.assertTrue(len(result.data) > 0, 'Poller data length should be non-zero')
            else:
                self.assertEqual(len(result.data), 0, 'Poller data should have 0 length')

    # @test(groups=['pollers_api2.tests', 'api2_delete_pollers'],
    #      depends_on_groups=['api2_current_data_get_pollers'])
    @depends(after='test_pollers_current_data_get')
    def test_delete_pollers(self):
        # """Test DELETE:api/2.0/pollers/:identifier"""
        for poller in self.__class__.created_pollers:
            Api().pollers_delete(identifier=poller["id"])
            result = self.__client.last_response

            self.assertEqual(204, result.status, msg=result.reason)

        try:
            Api().pollers_delete(identifier='does_not_exist')
        except ApiException as e:
            self.assertEqual(404, e.status, msg='Expected 404 status, received {}'.format(e.status))
