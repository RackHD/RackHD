'''
Copyright 2017, Dell, Inc.

Author(s):

UCS test script that tests:
-All the ucs service APIs
-The Discovery workflow
-The Catalog workflow

'''

import fit_path  # NOQA: unused import
import unittest
from common import fit_common
from nosedep import depends
import flogging
from nose.plugins.attrib import attr

logs = flogging.get_loggers()

UCSM_IP = fit_common.fitcfg().get('ucsm_ip')
UCSM_USER = fit_common.fitcfg().get('ucsm_user')
UCSM_PASS = fit_common.fitcfg().get('ucsm_pass')
UCS_SERVICE_URI = fit_common.fitcfg().get('ucs_service_uri')


@attr(all=True, regression=True, smoke=True, ucs=True)
class ucs_api(unittest.TestCase):

    def ucs_url_factory(self, api, identifier=None):
        """
        returns a fully qualified UCS API
        :param api:UCS API
        :param identifier: identify the ucs element in the catalog API
        :return:
        """

        if identifier is None:
            url = UCS_SERVICE_URI + "/" + api
        else:
            url = UCS_SERVICE_URI + "/" + api + "?identifier=" + identifier
        headers = {"ucs-user": UCSM_USER,
                   "ucs-password": UCSM_PASS,
                   "ucs-host": UCSM_IP}
        return (url, headers)

    @unittest.skipUnless("ucsm_ip" in fit_common.fitcfg(), "")
    def test_check_ucs_params(self):
        self.assertNotEqual(UCSM_IP, None, "Expected value for UCSM_IP other then None and found {0}"
                            .format(UCSM_IP))
        self.assertNotEqual(UCS_SERVICE_URI, None,
                            "Expected value for UCS_SERVICE_URI other then None and found {0}"
                            .format(UCS_SERVICE_URI))

    @depends(after=test_check_ucs_params)
    def test_ucs_log_in(self):
        """
        Test the /logIn ucs API
        :return:
        """
        url, headers = self.ucs_url_factory("login")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        self.assertNotEqual(api_data["json"], None, "Expected a token to be returned on login and received None")
        self.assertNotEqual(type(api_data["json"]), "unicode", "Unexpected Token was received on Login")

    @depends(after=test_check_ucs_params)
    def test_ucs_get_sys(self):
        """
        Test the /sys ucs API
        :return:
        """
        url, headers = self.ucs_url_factory("sys")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        self.assertIn("Fabric Interconnects", api_data["json"], "Results did not contain 'Fabric Interconnects'")

        self.assertIn("Servers", api_data["json"], "Results did not contain 'Servers")

        self.assertIn("FEX", api_data["json"], "Results did not contain 'FEX")

        self.assertIn("Chassis", api_data["json"], "Results did not contain 'Chassis")

    @depends(after=test_check_ucs_params)
    def test_ucs_get_rackmount(self):
        """
        Test the /rackmount ucs API
        :return:
        """
        url, headers = self.ucs_url_factory("rackmount")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertGreater(len(api_data["json"]), 0, "Found zero Rackmounts")
        # TO DO more in depth testing for the returned content such as mac validation, etc...

    @depends(after=test_check_ucs_params)
    def test_ucs_get_chassis(self):
        """
        Test the /chassis ucs API
        :return:
        """
        url, headers = self.ucs_url_factory("chassis")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        self.assertGreater(len(api_data["json"]), 0, "Zero chassis elements found")

        # TO DO more in depth testing for the returned content such as mac validation, etc...

    @depends(after=test_ucs_get_chassis)
    def test_ucs_get_serviceProfile(self):
        """
        Test the /serviceProfile ucs API
        :return:
        """
        url, headers = self.ucs_url_factory("serviceProfile")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        if len(api_data["json"]["ServiceProfile"]["members"]) == 0:
            raise unittest.SkipTest("No Service Profiles Defined")

        # TO DO more in depth testing for the returned content such as mac validation, etc...

    @depends(after=test_check_ucs_params)
    def test_api_20_ucs_get_catalog(self):
        """
        Test the /sys ucs API
        :return:
        """
        url, headers = self.ucs_url_factory("sys")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        total_elements = 0
        for elementTypes in api_data["json"]:
            for element in api_data["json"][str(elementTypes)]:
                url, headers = self.ucs_url_factory("catalog", identifier=element["relative_path"].split("/")[-1])
                api_data_c = fit_common.restful(url, rest_headers=headers)
                self.assertEqual(api_data_c['status'], 200,
                                 'Incorrect HTTP return code, expected 200, got:' + str(api_data_c['status']))
                total_elements += 1

        self.assertGreater(total_elements, 0, "Zero catalog elements found")
        # TO DO: deeper check on the catalog data

    def check_all_server_power_state(self, state):
        """
        Test to see if all Associated servers are in the specified state
        :return: True or False
        """

        url, headers = self.ucs_url_factory("serviceProfile")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        total_elements = 0
        for server in api_data["json"]["ServiceProfile"]["members"]:
            if server["assoc_state"] == "associated":
                url, headers = self.ucs_url_factory("power", identifier=str(server["path"]))
                api_data_c = fit_common.restful(url, rest_headers=headers)
                self.assertEqual(api_data_c['status'], 200,
                                 'Incorrect HTTP return code, expected 200, got:' + str(api_data_c['status']))
                self.assertEqual(api_data_c["json"]["serverState"], state,
                                 'Server ' + str(server["path"]) + ' reported power state ' +
                                 str(api_data_c["json"]["serverState"]) + ' expected: ' + state)
            total_elements += 1
        self.assertGreater(total_elements, 0, "Found zero elements")

    def set_all_server_power_state(self, state):
        """
        Use the POST /power ucs API to set the state of all servers
        :return:
        """

        url, headers = self.ucs_url_factory("serviceProfile")
        api_data = fit_common.restful(url, rest_headers=headers)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        total_elements = 0
        for server in api_data["json"]["ServiceProfile"]["members"]:
            if server["assoc_state"] == "associated":
                url, headers = self.ucs_url_factory("power", identifier=str(server["path"]))
                api_data_c = fit_common.restful(url + "&action=" + state, rest_headers=headers, rest_action='post')
                self.assertEqual(api_data_c['status'], 200,
                                 'Incorrect HTTP return code, expected 200, got:' + str(api_data_c['status']))
            total_elements += 1
        self.assertGreater(total_elements, 0, "Found zero elements")

    @depends(after=test_ucs_get_serviceProfile)
    def test_api_20_ucs_power(self):
        """
        Test the GET and POST api for server power state
        :return:
        """

        # first power off all servers
        self.set_all_server_power_state("off")
        # verify power state is down
        self.check_all_server_power_state("down")
        # now power on the servers
        self.set_all_server_power_state("on")
        # verify power state is up
        self.check_all_server_power_state("up")


if __name__ == '__main__':
    unittest.main()
