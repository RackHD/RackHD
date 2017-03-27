"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.

"""
import fit_path  # NOQA: unused import                                                                                          
import unittest
import flogging

from config.redfish1_0_config import config
from modules.redfish_auth import Auth
from on_http_redfish_1_0 import RedfishvApi as redfish
from on_http_redfish_1_0 import rest
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['redfish.session_service.tests'], depends_on_groups=['obm.tests'])
@attr(regression=True, smoke=True, schema_rf1_tests=True)
class SessionServiceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # setup test environment
        cls.__client = config.api_client
        cls.__sessionList = None
        cls.__session = None

        Auth.enable()

    @classmethod
    def tearDownClass(cls):
        # restore test environment
        Auth.disable()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.get_session_service'])
    def test_get_session_service(self):
        # """ Testing GET /SessionService """
        redfish().get_session_service()
        service = self.__get_data()
        logs.debug(dumps(service, indent=4))
        id = service.get('Id')
        self.assertEqual('SessionService', id, msg='unexpected id {0}, expected {1}'.format(id, 'SessionService'))
        sessions = service.get('Sessions')
        self.assertNotEqual(None, sessions, msg='Failed to get sessions')

    # @test(groups=['redfish.post_session'], depends_on_groups=['redfish.get_session_service'])
    @depends(after='test_get_session_service')
    def test_post_session(self):
        # """ Testing POST /SessionService/Sessions """
        body = {
            'UserName': 'admin',
            'Password': 'admin123'
        }
        redfish().post_session(payload=body)
        sessions = self.__get_data()
        self.__class__.__session = sessions.get('Id')
        self.assertNotEqual(None, self.__class__.__session)

    # @test(groups=['redfish.get_sessions'], depends_on_groups=['redfish.post_session'])
    @depends(after='test_post_session')
    def test_get_sessions(self):
        # """ Testing GET /SessionService/Sessions """
        redfish().get_sessions()
        sessions = self.__get_data()
        self.__class__.__sessionList = sessions.get('Members')

    # @test(groups=['redfish.get_session_info'], depends_on_groups=['redfish.get_sessions'])
    @depends(after='test_get_sessions')
    def test_get_session_info(self):
        # """ Testing GET /SessionService/Sessions/{identifier} """
        self.assertNotEqual(None, self.__class__.__sessionList)
        for member in self.__class__.__sessionList:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/SessionService/Sessions/')[1]
            redfish().get_session_info(dataId)
            session_ref = self.__get_data()
            logs.debug(dumps(session_ref, indent=4))
            id = session_ref.get('Id')
            self.assertEqual(dataId, id, msg='unexpected id {0}, expected {1}'.format(id, dataId))

    # @test(groups=['redfish.get_session_info_invalid'], depends_on_groups=['redfish.get_session_info'])
    @depends(after='test_get_session_info')
    def test_get_session_info_invalid(self):
        # """ Testing GET /SessionService/Sessions/{identifier} 404s properly"""
        self.assertNotEqual(None, self.__class__.__sessionList)
        for member in self.__class__.__sessionList:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/SessionService/Sessions/')[1]
            try:
                redfish().get_session_info(dataId + 'invalid')
                self.fail(msg='did not raise exception')
            except rest.ApiException as e:
                self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))
            break

    # @test(groups=['redfish.do_logout_session'], depends_on_groups=['redfish.get_session_info_invalid'])
    @depends(after='test_get_session_info_invalid')
    def test_do_logout_session(self):
        # """ Testing DELETE /SessionService/Sessions/{identifier} """
        redfish().do_logout_session(self.__class__.__session)
        try:
            redfish().get_session_info(self.__class__.__session)
            self.fail(msg='did not raise exception')
        except rest.ApiException as e:
            self.assertEqual(404, e.status, msg='unexpected response {0}, expected 404'.format(e.status))

        self.test_get_sessions()
        for member in self.__class__.__sessionList:
            dataId = member.get('@odata.id')
            dataId = dataId.split('/redfish/v1/SessionService/Sessions/')[1]
            self.assertNotEqual(self.__class__.__session, dataId)
