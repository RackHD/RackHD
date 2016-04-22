from proboscis import register
from proboscis import TestProgram
import modules.httpd as httpd
import argparse
import sys

def run_tests():

    import tests.api.v1_1 as api_1_1 
    import tests.api.v2_0 as api_2_0
    import tests.api.redfish_1_0 as api_redfish_1_0

    register(groups=['api-v1.1'], depends_on_groups=api_1_1.tests)
    register(groups=['api-v2.0'], depends_on_groups=api_2_0.tests)
    register(groups=['api-redfish-1.0'], depends_on_groups=api_redfish_1_0.tests)

    TestProgram().run_and_exit()

if __name__ == '__main__':
    # avoid eating valid proboscis args
    if len(sys.argv) > 1 and sys.argv[1] == '--httpd': 
        parser = argparse.ArgumentParser()
        parser.add_argument('--httpd', action='store_const', const=True)
        parser.add_argument('-a', '--address', default='0.0.0.0', required=False)
        parser.add_argument('-p', '--port', default=80, required=False)
        args = parser.parse_args()
        httpd.run_server(args.address,args.port)
        sys.exit(0)
    run_tests()
