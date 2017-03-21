from config.redfish1_0_config import *
from modules.logger import Log
from modules.redfish_auth import Auth
from on_http_redfish_1_0 import RedfishvApi as redfish
from on_http_redfish_1_0 import rest
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import loads,dumps
from proboscis import before_class
from proboscis import after_class


LOG = Log(__name__)

@test(groups=['redfish.session_service.tests'], depends_on_groups=['obm.tests'])
class SessionServiceTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__sessionList = None
        self.__session = None

    @before_class()
    def setup(self):
        """setup test environment"""
        Auth.enable()

    @after_class(always_run=True)
    def teardown(self):
        """ restore test environment """
        Auth.disable()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    @test(groups=['redfish.get_session_service'])
    def test_get_session_service(self):
        """ Testing GET /SessionService """
        redfish().get_session_service()
        service = self.__get_data()
        LOG.debug(service,json=True)
        id = service.get('Id')
        assert_equal('SessionService', id, message='unexpected id {0}, expected {1}'.format(id,'SessionService'))
        sessions = service.get('Sessions')
        assert_not_equal(None, sessions, message='Failed to get sessions')

    @test(groups=['redfish.post_session'], depends_on_groups=['redfish.get_session_service'])
    def test_post_session(self):
        """ Testing POST /SessionService/Sessions """
        body = {
            'UserName': 'admin',
            'Password': 'admin123'
        }
        redfish().post_session(payload=body)
        sessions = self.__get_data()
        self.__session = sessions.get('Id')
        assert_not_equal(None, self.__session)

    @test(groups=['redfish.get_sessions'], depends_on_groups=['redfish.post_session'])
    def test_get_sessions(self):
        """ Testing GET /SessionService/Sessions """
        redfish().get_sessions()
        sessions = self.__get_data()
        self.__sessionList = sessions.get('Members')

    @test(groups=['redfish.get_session_info'], depends_on_groups=['redfish.get_sessions'])
    def test_get_session_info(self):
        """ Testing GET /SessionService/Sessions/{identifier} """
        assert_not_equal(None, self.__sessionList)
        for member in self.__sessionList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/SessionService/Sessions/')[1]
            redfish().get_session_info(dataId)
            session_ref = self.__get_data()
            LOG.debug(session_ref,json=True)
            id = session_ref.get('Id')
            assert_equal(dataId, id, message='unexpected id {0}, expected {1}'.format(id,dataId))

    @test(groups=['redfish.get_session_info_invalid'], depends_on_groups=['redfish.get_session_info'])
    def test_get_session_info_invalid(self):
        """ Testing GET /SessionService/Sessions/{identifier} 404s properly"""
        assert_not_equal(None, self.__sessionList)
        for member in self.__sessionList:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/SessionService/Sessions/')[1]
            try:
                redfish().get_session_info(dataId + 'invalid')
                fail(message='did not raise exception')
            except rest.ApiException as e:
                assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))
            break

    @test(groups=['redfish.do_logout_session'], depends_on_groups=['redfish.get_session_info_invalid'])
    def test_do_logout_session(self):
        """ Testing DELETE /SessionService/Sessions/{identifier} """
        redfish().do_logout_session(self.__session)
        try:
            redfish().get_session_info(self.__session)
            fail(message='did not raise exception')
        except rest.ApiException as e:
            assert_equal(404, e.status, message='unexpected response {0}, expected 404'.format(e.status))

        self.test_get_sessions()
        for member in self.__sessionList:
            dataId = member.get('@odata.id')
            dataId = dataId.split('/redfish/v1/SessionService/Sessions/')[1]
            assert_not_equal(self.__session,dataId)


