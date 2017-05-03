from config.api2_0_config import *
import requests
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_true
from proboscis import test

@test(groups=['swagger.tests'])
class SwaggerTests:
    def __init__(self):
        print config.api_root
        print config.host
        self.swagger_path = '{0}{1}/swagger'.format(config.host, config.api_root)

    @test(groups=['swagger.tests.tags'])
    def test_tags(self):
        '''Basic validation of swagger object tags'''
        r = requests.get(self.swagger_path)
        assert_equal(200, r.status_code)

        swagger_def = r.json()

        # There should be exactly one tag named '/api/2.0'
        assert_equal(1, len(swagger_def['tags']))
        assert_equal('/api/2.0', swagger_def['tags'][0]['name'])
        assert_equal('RackHD 2.0 API', swagger_def['tags'][0]['description'])

        # All endpoints should be tagged with 'api/2.0'
        for path in swagger_def['paths']:
            for method in swagger_def['paths'][path]:
                assert_true('/api/2.0' in swagger_def['paths'][path][method]['tags'])
