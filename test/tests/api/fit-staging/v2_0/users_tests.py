"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

"""
import fit_path  # NOQA: unused import
import fit_common
import flogging


from config.api2_0_config import config
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from json import loads, dumps
from modules.auth2_0 import Auth
from nose.plugins.attrib import attr
from nosedep import depends

logs = flogging.get_loggers()


@attr(regression=False, smoke=False, users_api2_tests=True)
class UsersTests(fit_common.unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """setup test environment"""
        cls.__client = config.api_client
        Auth.enable()

    @classmethod
    def tearDownClass(cls):
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
        logs.info(dumps(token_blob, indent=4))
        config.api_client.host = stored_resource_path
        return token_blob['token']

    def test_users_start_clean(self):
        # """ Clear out any test users from previous script runs """
        # Note: A 'not found' error is expected and is ignored
        try:
            Api().remove_user(name='funtest-name')
        except:
            pass

        Api().list_users()
        users = self.__get_data()
        logs.debug(dumps(users, indent=4))
        found = False
        for user in users:
            if user.get('username') == 'funtest-name':
                found = True
                break
        self.assertFalse(found, msg='Test user was not removed')

    @depends(after=test_users_start_clean)
    def test_create_user(self):
        # """ Testing create new user  """
        newuser = {
            'username': 'funtest-name',
            'password': 'funtest123',
            'role': 'Administrator'
        }
        Api().add_user(body=newuser)
        Api().list_users()
        users = self.__get_data()
        logs.debug(dumps(users, indent=4))
        found = False
        for user in users:
            if newuser.get('username') == user.get('username'):
                self.assertEqual(newuser.get('role'), user.get('role'))
                found = True
                break
        self.assertTrue(found, msg='newly created user was not found')

    @depends(after='test_create_user')
    def test_validate_user_privilege(self):
        # """ Testing validate admin privileges  """
        user = {
            'username': 'funtest-name',
            'password': 'funtest123'
        }
        Api().get_user('funtest-name')
        logs.info(dumps(user, indent=4))
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
        logs.debug(dumps(users, indent=4))
        found = False
        for user in users:
            if newuser.get('username') == user.get('username'):
                self.assertEqual(newuser.get('role'), user.get('role'))
                found = True
                break
        self.assertTrue(found, msg='failed to create new user')

        Api().remove_user(name='funtest2-name')
        Api().list_users()
        users = self.__get_data()
        logs.debug(dumps(users, indent=4))
        found = False
        for user in users:
            if user.get('username') == 'funtest2-name':
                found = True
                break
        self.assertFalse(found, msg='failed to remove new user')
        # Restore config token
        config.api_client.default_headers['authorization'] = save_admin_token

    @depends(after='test_validate_user_privilege')
    def test_modify_user(self):
        # """ Testing modifying user information  """
        newuser = {
            'password': 'funtest123',
            'role': 'ReadOnly'
        }
        Api().modify_user(name='funtest-name', body=newuser)
        Api().list_users()
        users = self.__get_data()
        logs.debug(dumps(users, indent=4))
        found = False
        for user in users:
            if 'funtest-name' == user.get('username'):
                self.assertEqual(newuser.get('role'), user.get('role'))
                found = True
                break
        self.assertTrue(found, msg='newly modified user was not found')

    @depends(after='test_modify_user')
    def test_validate_user_readOnly(self):
        # """ Testing validate read Only privilege  """
        user = {
            'username': 'funtest-name',
            'password': 'funtest123'
        }
        Api().get_user('funtest-name')
        logs.info(dumps(user, indent=4))
        save_admin_token = config.api_client.default_headers['authorization']
        config.api_client.default_headers['authorization'] = 'JWT ' + self.get_auth_token(user)
        newuser = {
            'username': 'funtest2-name',
            'password': 'funtest123',
            'role': 'Administrator'
        }
        logs.info('should fail to create user')
        try:
            Api().add_user(body=newuser)
        except ApiException as e:
            self.assertEqual(403, e.status, msg='Expected 403 status, received {}'.format(e.status))

        logs.info('should be able to display users list')
        Api().list_users()
        users = self.__get_data()
        logs.debug(dumps(users, indent=4))
        self.assertNotEqual(0, len(users))
        # Restore config token
        config.api_client.default_headers['authorization'] = save_admin_token

    # depends_on_groups=['users_api2.create_user', 'users_api2.validate_readOnly_user'])
    @depends(after=['test_create_user', 'test_validate_user_readOnly'])
    def test_remove_user(self):
        # """ Testing DELETE user """
        Api().remove_user(name='funtest-name')
        Api().list_users()
        users = self.__get_data()
        logs.debug(dumps(users, indent=4))
        found = False
        for user in users:
            if user.get('username') == 'funtest-name':
                found = True
                break
        self.assertFalse(found, msg='newly created user was not removed')
