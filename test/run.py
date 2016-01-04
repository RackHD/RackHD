from proboscis import register
from proboscis import TestProgram

def run_tests():
    from tests.nodes_tests import NodesTests
    from tests.obm_tests import OBMTests
    from tests.amqp_tests import AMQPTests
    from tests.lookups_tests import LookupsTests
    from tests.profiles_tests import ProfilesTests

    groups_list  = [
            'integraton'
    ]
    depends_list = [
            'nodes.tests',
            'obm.tests',
            'amqp.tests',
            'lookups.tests',
            'profiles.tests'
    ]
    register(groups=groups_list, depends_on_groups=depends_list)
    TestProgram().run_and_exit()

if __name__ == '__main__':
    run_tests()

