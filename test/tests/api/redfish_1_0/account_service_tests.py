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

@test(groups=['redfish.account_service.tests'], depends_on_groups=['obm.tests'])
class AccountServiceTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__accounts = None
        self.__roles = None

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

    @test(groups=['redfish.get_account_service'])
    def test_get_account_service(self):
        """ Testing GET /AccountService """
        redfish().get_account_service()
        service = self.__get_data()
        LOG.debug(service,json=True)
        id = service.get('Id')
        assert_equal('AccountService', id, message='unexpected id {0}, expected {1}'.format(id,'AccountService'))
        accounts = service.get('Accounts')
        roles = service.get('Roles')
        assert_not_equal(None, accounts, message='Failed to get accounts')
        assert_not_equal(None, roles, message='Failed to get roles')

    @test(groups=['redfish.list_roles'], depends_on_groups=['redfish.get_account_service'])
    def test_list_roles(self):
        """ Testing GET /AcountService/Roles """
        redfish().list_roles()
        roles = self.__get_data()
        LOG.debug(roles,json=True)
        self.__roles = roles.get('Members')
        assert_equal(len(self.__roles), 3, message='expected role length to be 3')
        for member in self.__roles:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Roles/')[1]
            redfish().get_role(dataId)
            role = self.__get_data()
            LOG.debug(role,json=True)
            name = role.get('Name')
            assert_equal(dataId, name, message='unexpected name {0}, expected {1}'.format(name,dataId))

    @test(groups=['redfish.get_accounts'], depends_on_groups=['redfish.get_account_service'])
    def test_get_accounts(self):
        """ Testing GET /AcountService/Accounts """
        redfish().get_accounts()
        accounts = self.__get_data()
        LOG.debug(accounts,json=True)
        self.__accounts = accounts.get('Members')
        for member in self.__accounts:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Accounts/')[1]
            redfish().get_account(dataId)
            account = self.__get_data()
            LOG.debug(account,json=True)
            username = account.get('UserName')
            assert_equal(dataId, username, message='unexpected username {0}, expected {1}'.format(username,dataId))

    @test(groups=['redfish.create_account'], depends_on_groups=['redfish.get_accounts'])
    def test_create_account(self):
        """ Testing POST /AcountService/Accounts """
        body = {
            'UserName': 'funtest-name',
            'Password': 'funtest123',
            'RoleId': 'Administrator'
        }
        redfish().create_account(payload=body)
        self.test_get_accounts()
        found = False
        for member in self.__accounts:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Accounts/')[1]
            if dataId == 'funtest-name':
                found = True
                redfish().get_account(dataId)
                account = self.__get_data()
                assert_equal(account.get('RoleId'), 'Administrator', message='unexpected RoleId')
                break
        if not found:
            fail(message='newly created user was not found')

    @test(groups=['redfish.modify_account'], depends_on_groups=['redfish.create_account'])
    def test_modify_account(self):
        """ Testing PATCH /AcountService/Accounts/{name} """
        body = {
            'Password': 'funtest456',
            'RoleId': 'ReadOnly'
        }
        redfish().modify_account('funtest-name', payload=body)
        redfish().get_account('funtest-name')
        account = self.__get_data()
        assert_equal(account.get('RoleId'), 'ReadOnly', message='unexpected RoleId')

    @test(groups=['redfish.remove_account'], depends_on_groups=['redfish.create_account'])
    def test_remove_account(self):
        redfish().remove_account('funtest-name')
        self.test_get_accounts()
        found = False
        for member in self.__accounts:
            dataId = member.get('@odata.id')
            assert_not_equal(None,dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Accounts/')[1]
            if dataId == 'funtest-name':
                fail(message='failed to delete account')



