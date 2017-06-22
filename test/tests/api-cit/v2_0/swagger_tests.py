'''
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
'''
import fit_path  # NOQA: unused import
import fit_common
import flogging
import requests

from config.api2_0_config import config
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


@attr(regression=False, smoke=True, swagger_api2_tests=True)
class SwaggerTests(fit_common.unittest.TestCase):
    def setUp(self):
        logs.info(config.api_root)
        logs.info(config.host)
        self.swagger_path = '{0}{1}/swagger'.format(config.host, config.api_root)

    # @test(groups=['swagger.tests.tags'])
    def test_swagger_tags(self):
        # """Basic validation of swagger object tags"""
        r = requests.get(self.swagger_path)
        self.assertEqual(200, r.status_code)

        swagger_def = r.json()

        # There should be exactly one tag named '/api/2.0'
        self.assertEqual(1, len(swagger_def['tags']))
        self.assertEqual('/api/2.0', swagger_def['tags'][0]['name'])
        self.assertEqual('RackHD 2.0 API', swagger_def['tags'][0]['description'])

        # All endpoints should be tagged with 'api/2.0'
        for path in swagger_def['paths']:
            for method in swagger_def['paths'][path]:
                logs.debug("Checking method %s, %s", method, swagger_def['paths'][path][method].get('summary'))
                self.assertTrue('/api/2.0' in swagger_def['paths'][path][method]['tags'])
