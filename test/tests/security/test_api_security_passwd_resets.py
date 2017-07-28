'''
Copyright 2015, DellEMC LLC

   ScriptName: test_api_security_passwd_resets.py
       Author: Torrey Cuthbert
        Email: torrey.cuthbert@dell.com
  Create Date: 07/28/2017

      Purpose: This script consists of cases intended to test RackHD login functions.
               As of date, there are three user account roles (Administrator, Operator, and ReadOnly).
               We will first test the RackHD endpoint's ability to create an account for each of these
               roles for both RackHD and Redfish interfaces (redfish=False).  We will then test the
               Redfish endpoint's ability to also create Redfish and RackHD accounts (Redfish=True).
               In both cases, all user roles will have established accounts in both endpoints and
               will possess tokens for role base access and permission.

           EX: python run_tests.py -stack 2
                                   -config dellemc-test/config-mn/
                                   -test tests/security/test_api_security_passwd_resets.py
               python run_tests.py -stack vagrant -test tests/security/test_api_security_passwd_resets.py
'''

import sys
import flogging
import fit_common
import exrex
from nose.plugins.attrib import attr
sys.path.append(fit_common.TEST_PATH + "/classes")
from classes.administrator import Administrator
from classes.readonly import ReadOnly
from classes.operator import Operator

# Globals
logs = flogging.get_loggers()


# Helper functions
def createUsername():
    return exrex.getone('[a-zA-Z]{1}[a-zA-Z0-9._\-]{1,}')


@attr(regression=False, smoke=True, security=True)
class TestCase01(fit_common.unittest.TestCase):

    def setUp(self):
        global admin, readonly, operator
        admin = Administrator(createUsername(), 'passwd', 'Administrator', redfish=False)
        operator = Operator(createUsername(), 'passwd', 'Operator', redfish=False)
        readonly = ReadOnly(createUsername(), 'passwd', 'ReadOnly', redfish=False)
        logs.debug_3("setUP() created the following accounts for testing")
        logs.debug_3("   admin => %s", admin.username)
        logs.debug_3("operator => %s", operator.username)
        logs.debug_3("readonly => %s", readonly.username)

    def tearDown(self):
        logs.debug_3("running tearDown() to delete following test accounts")
        logs.debug_3("   admin => %s", admin.username)
        logs.debug_3("operator => %s", operator.username)
        logs.debug_3("readonly => %s", readonly.username)
        if isinstance(admin, Administrator):
            admin.deleteRedfishUserAccount()
        if isinstance(operator, Operator):
            operator.deleteRedfishUserAccount()
        if isinstance(readonly, ReadOnly):
            readonly.deleteRedfishUserAccount()

    def shortDescription(self):
        logs.info("\n\n\
            This scenario tests each roles ability to change its own password.\n\
            A successful test creates an Administrator, ReadOnly, and Operator user account each\n\
            obtaining session tokens for both RackHD and Redfish APIs.\n\
            Only the administrator should be able to change their own passwords\n\n")

    def test_rackhd_system_roles_patch(self):
        pass
        self.assertIsNotNone(admin)
        http_resp_code = admin.changeRackHDPasswd('mypasswd', admin.rackhd_token)
        if http_resp_code is not None:
            self.assertEqual(http_resp_code, 200, 'Incorrect HTTP return code, expected 200, got: ' + str(http_resp_code))
        else:
            self.skip('Skipping test. API is unavailable')
        self.assertIsNotNone(operator)
        http_resp_code = operator.changeRackHDPasswd('mypasswd', operator.rackhd_token)
        if http_resp_code is not None:
            self.assertEqual(http_resp_code, 400, 'Incorrect HTTP return code, expected 400, got: ' + str(http_resp_code))
            logs.info("RAC-4795, expected response should be 401")
        else:
            self.skip('Skipping test. API is unavailable')
        self.assertIsNotNone(readonly)
        http_resp_code = readonly.changeRackHDPasswd('mypasswd', readonly.rackhd_token)
        if http_resp_code is not None:
            self.assertEqual(http_resp_code, 400, 'Incorrect HTTP return code, expected 401, got: ' + str(http_resp_code))
            logs.info("RAC-4795, marking passed, expected response should be 401")
        else:
            self.skip('Skipping test. API is unavailable')


@attr(regression=False, smoke=True, security=True)
class TestCase02(fit_common.unittest.TestCase):

    def setUp(self):
        global admin, readonly, operator
        admin = Administrator(createUsername(), 'passwd', 'Administrator', redfish=True)
        readonly = ReadOnly(createUsername(), 'passwd', 'ReadOnly', redfish=True)
        operator = Operator(createUsername(), 'passwd', 'Operator', redfish=True)
        logs.info("setUP() created the following accounts for testing")
        logs.info("   admin => %s", admin.username)
        logs.info("readonly => %s", readonly.username)
        logs.info("operator => %s", operator.username)

    def tearDown(self):
        logs.info("running tearDown() to delete following test accounts")
        logs.info("   admin => %s", admin.username)
        logs.info("readonly => %s", readonly.username)
        logs.info("operator => %s", operator.username)
        if isinstance(admin, Administrator):
            admin.deleteRedfishUserAccount()
        if isinstance(operator, Operator):
            operator.deleteRedfishUserAccount()
        if isinstance(readonly, ReadOnly):
            readonly.deleteRedfishUserAccount()

    def shortDescription(self):
        logs.info("\n\n\
            This scenario tests RackHD's setup administrative login credentials as well as the\n\
            system's ability to create both RackHD and Redfish accounts via the Redfish API\n\
            A successful test creates an Administrator, ReadOnly, and Operator user account each\n\
            obtaining session tokens for both RackHD and Redfish APIs\n\n")

    def test_redfish_system_roles_login_success(self):
        self.assertIsNotNone(admin)
        self.assertIsNotNone(readonly)
        self.assertIsNotNone(operator)
