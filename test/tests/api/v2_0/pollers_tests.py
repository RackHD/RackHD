from config.api2_0_config import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from proboscis.asserts import *
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)

@test(groups=['pollers_api2.tests'])
class PollersTests(object):
    def __init__(self):
        self.__client = config.api_client

    @test(groups=['pollers_api2.tests', 'api2_get_pollers_library'])
    def get_pollers_lib(self):
        """Test GET:api/2.0/pollers/library"""
        Api().pollers_lib_get()
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)

        assert_equal(200, result.status, message=result.reason)

        names = [lib['name'] for lib in data]
        assert_true('ipmi' in names and 'snmp' in names, names)

        for lib in data:
            assert_true('config' in lib.keys())

        self._poller_libs = data

    @test(groups=['pollers_api2.tests', 'api2_get_pollers_library_by_id'],
          depends_on_groups=['api2_get_pollers_library'])
    def get_pollers_lib_by_id(self):
        """Test GET:api/2.0/pollers/library/:identifier"""
        for lib in self._poller_libs:
            Api().pollers_lib_by_id_get(identifier=lib['name'])
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)

            assert_equal(200, result.status, message=result.reason)
            assert_equal(lib, data)

        try:
            Api().pollers_lib_by_id_get(identifier='not_a_real_poller')
        except ApiException as e:
            assert_true(404, e.status)

    @test(groups=['pollers_api2.tests', 'api2_get_pollers'])
    def get_pollers(self):
        """Test GET:api/2.0/pollers"""
        Api().pollers_get()
        result = self.__client.last_response
        data = loads(self.__client.last_response.data)

        assert_equal(200, result.status, message=result.reason)
        for poller in data:
            keys = poller.keys()
            assert_true('config' in keys)
            assert_true('type' in keys)
            assert_true('pollInterval' in keys)

        self._pollers = data

    @test(groups=['pollers_api2.tests', 'api2_get_pollers_by_id'],
          depends_on_groups=['api2_get_pollers'])
    def get_pollers_by_id(self):
        """Test GET:api/2.0/pollers/:identifier"""
        for poller in self._pollers:
            Api().pollers_id_get(identifier=poller['id'])
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)

            assert_equal(200, result.status, message=result.reason)
            assert_equal(data, poller)

        try:
            Api().pollers_id_get(identifier='does_not_exist')
        except ApiException as e:
            assert_true(404, e.status)

    @test(groups=['pollers_api2.tests', 'api2_create_pollers'])
    def create_pollers(self):
        """Test POST:api/2.0/pollers"""
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

        self._created_pollers = []
        for poller in pollers:
            Api().pollers_post(poller)
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)

            assert_equal(201, result.status, message=result.reason)
            for key in poller.keys():
                assert_equal(poller[key], data[key])

            self._created_pollers.append(data)

    @test(groups=['pollers_api2.tests', 'api2_patch_pollers'],
          depends_on_groups=['api2_create_pollers'])
    def pollers_patch(self):
        """Test PATCH:api/2.0/pollers/:identifier"""
        patch_data = {
            "pollInterval": 5000
        }
        for poller in self._created_pollers:
            Api().pollers_patch(poller['id'], patch_data)
            result = self.__client.last_response
            data = loads(self.__client.last_response.data)

            assert_equal(200, result.status, message=result.reason)
            assert_equal(5000, data['pollInterval'])
            poller = data

        try:
            Api().pollers_patch('does_not_exist', {})
        except ApiException as e:
            assert_true(404, e.status)

    @test(groups=['pollers_api2.tests', 'api2_data_get_pollers'],
          depends_on_groups=['api2_get_pollers', 'api2_patch_pollers'])
    def pollers_data_get(self):
        """Test GET:/api/2.0/pollers/:identifier/data"""
        all_pollers = self._pollers + self._created_pollers
        for poller in all_pollers:
            try:
                Api().pollers_data_get(poller['id'])
                result = self.__client.last_response

                assert_true(poller.get('lastFinished', False))
                assert_equal(200, result.status, message=result.reason)
            except ApiException as e:
                assert_false(poller.get('lastFinished', False))
                assert_equal(404, e.status)

    @test(groups=['pollers_api2.tests', 'api2_current_data_get_pollers'],
          depends_on_groups=['api2_get_pollers', 'api2_data_get_pollers'])
    def pollers_current_data_get(self):
        """Test GET:/api/2.0/pollers/:identifier/data/current"""
        all_pollers = self._pollers + self._created_pollers
        for poller in all_pollers:
            try:
                Api().pollers_current_data_get(poller['id'])
                result = self.__client.last_response

                assert_true(poller.get('lastFinished', False))
                assert_equal(200, result.status, message=result.reason)
            except ApiException as e:
                assert_false(poller.get('lastFinished', False))
                assert_equal(404, e.status)

    @test(groups=['pollers_api2.tests', 'api2_delete_pollers'],
          depends_on_groups=['api2_current_data_get_pollers'])
    def delete_pollers(self):
        """Test DELETE:api/2.0/pollers/:identifier"""
        for poller in self._created_pollers:
            Api().pollers_delete(identifier=poller["id"])
            result = self.__client.last_response

            assert_equal(204, result.status, message=result.reason)

        try:
            Api().pollers_delete(identifier='does_not_exist')
        except ApiException as e:
            assert_true(404, e.status)

