from config.api2_0_config import config
from config.amqp import *
from modules.logger import Log
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0 import rest
from on_http_api2_0.rest import ApiException
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis import test
from nodes_tests import NodesTests
from json import loads
from json import dumps
from time import sleep
from modules.auth2_0 import Auth
from proboscis import before_class
from proboscis import after_class
from proboscis.asserts import fail


LOG = Log(__name__)

@test(groups=['users_api2.tests'], depends_on_groups=['obm.tests'])
class UsersTests(object):

    def __init__(self):
        self.__client = config.api_client        

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

    def get_auth_token(self, user):
        """ call /login to get auth_token """
        stored_resource_path = config.api_client.host
        resource_path = '/login'
        method = 'POST'
        config.api_client.host = config.host_authed
        config.api_client.call_api(resource_path, method, body=user)
        token_blob = loads(config.api_client.last_response.data)
        LOG.info(token_blob, json=True)
        config.api_client.host = stored_resource_path
        return token_blob['token']

    @test(groups=['users_api2.create_user'])
    def test_create_user(self):
        """ Testing create new user  """
        newuser = {
            'username': 'funtest-name',
            'password': 'funtest123',
            'role': 'Administrator'
        }
        Api().add_user(body=newuser)
        Api().list_users()
        users = self.__get_data()
        LOG.debug(users,json=True)
        found = False
        for user in users:
            if newuser.get('username') == user.get('username') :
               found = True
               assert_equal(newuser.get('role'), user.get('role'))
        if not found:
            fail(message='newly created user was not found')

    @test(groups=['users_api2.validate_admin_user'], depends_on_groups=['users_api2.create_user'])
    def test_validate_user_privilege(self):
        """ Testing validate admin privileges  """
        user = {
            'username': 'funtest-name',
            'password': 'funtest123'
        }
        Api().get_user('funtest-name')
        found_user = self.__get_data()
        LOG.info(user,json=True)
        save_admin_token = config.api_client.default_headers['authorization']
        config.api_client.default_headers['authorization'] = 'JWT ' + self.get_auth_token(user)
        newuser = {
            'username': 'funtest2-name',
            'password': 'funtest123',
            'role': 'Administrator'
        }
        Api().add_user(body=newuser)
        Api().list_users()
        users = self.__get_data()
        LOG.debug(users,json=True)
        found = False
        for user in users:
            if newuser.get('username') == user.get('username') :
               found = True
               assert_equal(newuser.get('role'), user.get('role'))
        if not found:
            fail(message='failed to create new user')

        Api().remove_user(name='funtest2-name')
        Api().list_users()
        users = self.__get_data()
        LOG.debug(users,json=True)
        found = False
        for user in users:
            if  user.get('username') == 'funtest2-name' :
               found = True
        if found:
            fail(message='failed to remove new user')
        #Restore config token
        config.api_client.default_headers['authorization'] = save_admin_token
        

    @test(groups=['users_api2.modify_user'], depends_on_groups=['users_api2.validate_admin_user'])
    def test_modify_user(self):
        """ Testing modifying user information  """
        newuser = {
            'password': 'funtest123',
            'role': 'ReadOnly'
        }
        Api().modify_user(name='funtest-name', body=newuser)
        Api().list_users()
        users = self.__get_data()
        LOG.debug(users,json=True)
        found = False
        for user in users:
            if 'funtest-name' == user.get('username') :
               found = True
               assert_equal(newuser.get('role'), user.get('role'))
        if not found:
            fail(message='newly modified user was not found')

    @test(groups=['users_api2.validate_readOnly_user'], depends_on_groups=['users_api2.modify_user'])
    def test_validate_user_readOnly(self):
        """ Testing validate read Only privilege  """
        user = {
            'username': 'funtest-name',
            'password': 'funtest123'
        }
        Api().get_user('funtest-name')
        found_user = self.__get_data()
        LOG.info(user,json=True)
        save_admin_token = config.api_client.default_headers['authorization']
        config.api_client.default_headers['authorization'] = 'JWT ' + self.get_auth_token(user)
        newuser = {
            'username': 'funtest2-name',
            'password': 'funtest123',
            'role': 'Administrator'
        }
        LOG.info('should fail to create user')
        try :
            Api().add_user(body=newuser)
        except ApiException as e:
            assert_equal(403, e.status)
        LOG.info('should be able to display users list') 
        Api().list_users()
        users = self.__get_data()
        LOG.debug(users,json=True)
        assert_not_equal(0,len(users))
        #Restore config token
        config.api_client.default_headers['authorization'] = save_admin_token
        

    @test(groups=['users_api2.remove_user'], depends_on_groups=['users_api2.create_user', 'users_api2.validate_readOnly_user'])
    def test_remove_user(self):
        """ Testing DELETE user """
        Api().remove_user(name='funtest-name')
        Api().list_users()
        users = self.__get_data()
        LOG.debug(users,json=True)
        found = False
        for user in users:
            if  user.get('username') == 'funtest-name' :
               found = True
        if found:
            fail(message='newly created user was not removed')
