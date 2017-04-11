"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import fit_path  # NOQA: unused import                                                                                          
import unittest
import flogging

from config.redfish1_0_config import config
from modules.redfish_auth import Auth
from on_http_redfish_1_0 import RedfishvApi as redfish
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['redfish.account_service.tests'], depends_on_groups=['obm.tests'])
@attr(regression=True, smoke=True, account_service_rf1_tests=True)
class AccountServiceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.__client = config.api_client
        cls.__accounts = None

        # setup test environment
        Auth.enable()

    @classmethod
    def tearDownClass(cls):
        # """ restore test environment """
        Auth.disable()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    # @test(groups=['redfish.get_account_service'])
    def test_get_account_service(self):
        # """ Testing GET /AccountService """
        redfish().get_account_service()
        service = self.__get_data()
        logs.debug(" Service: ")
        logs.debug(dumps(service, indent=4))
        id = service.get('Id')
        self.assertEqual('AccountService', id, msg='unexpected id {0}, expected {1}'.format(id, 'AccountService'))
        accounts = service.get('Accounts')
        roles = service.get('Roles')
        self.assertNotEqual(None, accounts, msg='Failed to get accounts')
        self.assertNotEqual(None, roles, msg='Failed to get roles')

    # @test(groups=['redfish.list_roles'], depends_on_groups=['redfish.get_account_service'])
    @depends(after='test_get_account_service')
    def test_list_roles(self):
        # """ Testing GET /AcountService/Roles """
        redfish().list_roles()
        roles = self.__get_data()
        logs.debug(" Roles: ")
        logs.debug(dumps(roles, indent=4))
        __roles = roles.get('Members')
        self.assertEqual(len(__roles), 3, msg='expected role length to be 3')
        for member in __roles:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Roles/')[1]
            redfish().get_role(dataId)
            role = self.__get_data()
            logs.debug(dumps(role, indent=4))
            name = role.get('Name')
            self.assertEqual(dataId, name, msg='unexpected name {0}, expected {1}'.format(name, dataId))

    # @test(groups=['redfish.get_accounts'], depends_on_groups=['redfish.get_account_service'])
    @depends(after='test_get_account_service')
    def test_get_accounts(self):
        # """ Testing GET /AcountService/Accounts """
        redfish().get_accounts()
        accounts = self.__get_data()
        logs.debug(" Accounts: ")
        logs.debug(dumps(accounts, indent=4))
        self.__class__.__accounts = accounts.get('Members')
        for member in self.__class__.__accounts:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Accounts/')[1]
            redfish().get_account(dataId)
            account = self.__get_data()
            logs.debug(dumps(account, indent=4))
            username = account.get('UserName')
            self.assertEqual(dataId, username, msg='unexpected username {0}, expected {1}'.format(username, dataId))

    @depends(after='test_get_accounts')
    def test_clear_test_account(self):
        # """ Clearing out any existing test Accounts funtest-name """
        self.test_get_accounts()
        for member in self.__class__.__accounts:
            dataId = member.get('@odata.id')
            if dataId:
                dataId = dataId.split('/redfish/v1/AccountService/Accounts/')[1]
                if dataId == 'funtest-name':
                    # If user tries to rerun after a failed test, this should clear out left overs
                    redfish().remove_account('funtest-name')

    # @test(groups=['redfish.create_account'], depends_on_groups=['redfish.get_accounts'])
    @depends(after='test_clear_test_account')
    def test_create_account(self):
        # """ Testing POST /AcountService/Accounts """
        body = {
            'UserName': 'funtest-name',
            'Password': 'funtest123',
            'RoleId': 'Administrator'
        }
        logs.debug(" Creating Account: ")
        redfish().create_account(payload=body)
        self.test_get_accounts()
        found = False
        for member in self.__class__.__accounts:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Accounts/')[1]
            if dataId == 'funtest-name':
                found = True
                redfish().get_account(dataId)
                account = self.__get_data()
                logs.debug(dumps(account, indent=4))
                self.assertEqual(account.get('RoleId'), 'Administrator', msg='unexpected RoleId')
                break
        if not found:
            self.fail(msg='newly created user was not found')

    # @test(groups=['redfish.modify_account'], depends_on_groups=['redfish.create_account'])
    @depends(after='test_create_account')
    def test_modify_account(self):
        # """ Testing PATCH /AcountService/Accounts/{name} """
        body = {
            'Password': 'funtest456',
            'RoleId': 'ReadOnly'
        }
        logs.debug(" Modifying Account: ")
        redfish().modify_account('funtest-name', payload=body)
        redfish().get_account('funtest-name')
        account = self.__get_data()
        logs.debug(dumps(account, indent=4))
        self.assertEqual(account.get('RoleId'), 'ReadOnly', msg='unexpected RoleId')

    # @test(groups=['redfish.remove_account'], depends_on_groups=['redfish.create_account'])
    @depends(after='test_modify_account')
    def test_remove_account(self):
        # """ Testing DELETE /AcountService/Accounts/{name} """
        redfish().remove_account('funtest-name')
        self.test_get_accounts()
        for member in self.__class__.__accounts:
            dataId = member.get('@odata.id')
            self.assertNotEqual(None, dataId)
            dataId = dataId.split('/redfish/v1/AccountService/Accounts/')[1]
            if dataId == 'funtest-name':
                self.fail(msg='failed to delete account')
