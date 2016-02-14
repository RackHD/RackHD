from proboscis import register
from proboscis import TestProgram

def run_tests():

    import tests.api.v1_1 as api_1_1 
    import tests.api.v2_0 as api_2_0
    import tests.api.redfish_1_0 as api_redfish_1_0

    register(groups=['api-v1.1'], depends_on_groups=api_1_1.tests)
    register(groups=['api-v2.0'], depends_on_groups=api_2_0.tests)
    register(groups=['api-redfish-1.0'], depends_on_groups=api_redfish_1_0.tests)

    TestProgram().run_and_exit()

if __name__ == '__main__':
    run_tests()
