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


@attr(all=True, regression=True, smoke=True, ucs=True)
class ucs_api(unittest.TestCase):

    UCS_IP = fit_common.fitcfg().get("ucs_ip")
    UCS_PORT = fit_common.fitcfg().get("ucs_port")
    RACKHD_IP = fit_common.fitcfg().get("rackhd_host")

    def ucs_url_factory(self, api, identifier=None):
        """
        returns a fully qualified UCS API
        :param api:UCS API
        :param identifier: identify the ucs element in the catalog API
        :return:
        """
        ucs_service = self.RACKHD_IP + ":" + self.UCS_PORT + "/"
        ucs_manager = self.UCS_IP
        if identifier is None:
            url = "http://" + ucs_service + api + "?host=" + ucs_manager + " &user=ucspe&password=ucspe"
        else:
            url = "http://" + ucs_service + api + "?host=" + ucs_manager + " &user=ucspe&password=ucspe"\
                  "&identifier=" + identifier
        return url

    @unittest.skipUnless("ucs_ip" in fit_common.fitcfg(), "")
    def test_check_ucs_params(self):
        self.assertNotEqual(self.UCS_IP, None, "Expected value for UCS_IP other then None and found {0}"
                            .format(self.UCS_IP))
        self.assertNotEqual(self.UCS_PORT, None, "Expected value for UCS_PORT other then None and found {0}"
                            .format(self.UCS_IP))

    @depends(after=test_check_ucs_params)
    def test_ucs_log_in(self):
        """
        Test the /logIn ucs API
        :return:
        """
        url = self.ucs_url_factory("login")
        api_data = fit_common.restful(url)
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
        url = self.ucs_url_factory("sys")
        api_data = fit_common.restful(url)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

        self.assertEqual(len(api_data["json"]["Fabric Interconnects"]), 2,
                         "Expected 2 Fabric Interconnects but found {0}"
                         .format(len(api_data["json"]["Fabric Interconnects"])))
        self.assertEqual(len(api_data["json"]["Servers"]), 7, "Expected 7 Servers but found {0}"
                         .format(len(api_data["json"]["Servers"])))
        self.assertEqual(len(api_data["json"]["FEX"]), 2, "Expected 2 FEX but found {0}"
                         .format(len(api_data["json"]["FEX"])))
        self.assertEqual(len(api_data["json"]["Chassis"]), 4, "Expected 2 Chassis but found {0}"
                         .format(len(api_data["json"]["Chassis"])))

    @depends(after=test_check_ucs_params)
    def test_ucs_get_rackmount(self):
        """
        Test the /rackmount ucs API
        :return:
        """
        url = self.ucs_url_factory("rackmount")
        api_data = fit_common.restful(url)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertGreaterEqual(len(api_data["json"]), 1, "Expected 1  or more Rackmounts but found {0}".
                                format(len(api_data["json"])))
        # TO DO more in depth testing for the returned content such as mac validation, etc...

    @depends(after=test_check_ucs_params)
    def test_ucs_get_chassis(self):
        """
            Test the /chassis ucs API
            :return:
            """
        url = self.ucs_url_factory("chassis")
        api_data = fit_common.restful(url)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertGreaterEqual(len(api_data["json"]), 4, "Expected 4 chassis or more but found {0}".
                                format(len(api_data["json"])))
        # TO DO more in depth testing for the returned content such as mac validation, etc...

    @depends(after=test_check_ucs_params)
    def test_api_20_ucs_get_catalog(self):
        """
        Test the /sys ucs API
        :return:
        """
        url = self.ucs_url_factory("sys")
        api_data = fit_common.restful(url)
        self.assertEqual(api_data['status'], 200,
                         'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        total_elements = 0
        for elementTypes in api_data["json"]:
            for element in api_data["json"][str(elementTypes)]:
                url = self.ucs_url_factory("catalog", identifier=element["relative_path"].split("/")[-1])
                api_data_c = fit_common.restful(url)
                self.assertEqual(api_data['status'], 200,
                                 'Incorrect HTTP return code, expected 200, got:' + str(api_data_c['status']))
                total_elements += 1
        self.assertGreaterEqual(total_elements, 15, "Expected at least 15 elements but found {0}"
                                .format(total_elements))
        # TO DO: deeper check on the catalog data


if __name__ == '__main__':
    unittest.main()
