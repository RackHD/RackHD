'''
Copyright 2015, DellEMC LLC

   ScriptName: test_api_security_login.py
       Author: Torrey Cuthbert
        Email: torrey.cuthbert@dell.com
  Create Date: 04/09/2017

      Purpose: This script consists of cases intended to test RackHD login functions.
               As of date, there are three user account roles (Administrator, Operator, and ReadOnly).
               We will first test the RackHD endpoint's ability to create an account for each of these
               roles for both RackHD and Redfish interfaces (redfish=False).  We will then test the
               Redfish endpoint's ability to also create Redfish and RackHD accounts (Redfish=True).
               In both cases, all user roles will have established accounts in both endpoints and
               will possess tokens for role base access and permission.

           EX: python run_tests.py -stack 2 -config dellemc-test/config-mn/ -test tests/security/test_api_security_login.py
               python run_tests.py -stack 2 -test tests/security/test_api_security_login.py
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
        if fit_common.VERBOSITY >= 5:
            logs.info("Running test: %s", self._testMethodName)
        global admin, readonly, operator
        admin = Administrator(createUsername(), 'passwd', 'Administrator', redfish=False)
        readonly = ReadOnly(createUsername(), 'passwd', 'ReadOnly', redfish=False)
        operator = Operator(createUsername(), 'passwd', 'Operator', redfish=False)
        if fit_common.VERBOSITY >= 5:
            logs.info("setUP() created the following accounts for testing")
            logs.info("   admin => %s", admin.username)
            logs.info("readonly => %s", readonly.username)
            logs.info("operator => %s", operator.username)

    def tearDown(self):
        if fit_common.VERBOSITY >= 5:
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
        logs.info(" ")
        logs.info("This scenario tests RackHD's setup administrative login credentials as well as the")
        logs.info("system's ability to create both RackHD and Redfish accounts via the RackHD API")
        logs.info("A successful test creates an Administrator, ReadOnly, and Operator user account each")
        logs.info("obtaining session tokens for both RackHD and Redfish APIs.")
        logs.info(" ")

    def test_rackhd_system_roles_login_success(self):
        self.assertIsNotNone(admin)
        self.assertIsNotNone(readonly)
        self.assertIsNotNone(operator)

@attr(regression=False, smoke=True, security=True)
class TestCase02(fit_common.unittest.TestCase):

    def setUp(self):
        if fit_common.VERBOSITY >= 5:
            logs.info("Running test: %s", self._testMethodName)
        global admin, readonly, operator
        admin = Administrator(createUsername(), 'passwd', 'Administrator', redfish=True)
        readonly = ReadOnly(createUsername(), 'passwd', 'ReadOnly', redfish=True)
        operator = Operator(createUsername(), 'passwd', 'Operator', redfish=True)
        if fit_common.VERBOSITY >= 5:
            logs.info("setUP() created the following accounts for testing")
            logs.info("   admin => %s", admin.username)
            logs.info("readonly => %s", readonly.username)
            logs.info("operator => %s", operator.username)

    def tearDown(self):
        if fit_common.VERBOSITY >= 5:
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
        logs.info(" ")
        logs.info("This scenario tests RackHD's setup administrative login credentials as well as the")
        logs.info("system's ability to create both RackHD and Redfish accounts via the Redfish API")
        logs.info("A successful test creates an Administrator, ReadOnly, and Operator user account each")
        logs.info("obtaining session tokens for both RackHD and Redfish APIs.")
        logs.info(" ")

    def test_redfish_system_roles_login_success(self):
        self.assertIsNotNone(admin)
        self.assertIsNotNone(readonly)
        self.assertIsNotNone(operator)
