from proboscis import register
from proboscis import TestProgram


def run_tests():
    from tests.nodes_tests import NodesTests
    from tests.obm_tests import OBMTests
    from tests.amqp_tests import AMQPTests
    from tests.lookups_tests import LookupsTests
    from tests.profiles_tests import ProfilesTests
    from tests.config_tests import ConfigTests
    from tests.workflowTasks_tests import WorkflowTasksTests
    from tests.workflows_tests import WorkflowsTests

    groups_list = [
            'integraton'
    ]
    depends_list = [
            'nodes.tests',
            'obm.tests',
            'amqp.tests',
            'lookups.tests',
            'profiles.tests'
            'config.tests',
            'workflowTasks.tests',
            'workflows.tests'

    ]
    register(groups=groups_list, depends_on_groups=depends_list)
    TestProgram().run_and_exit()

if __name__ == '__main__':
    run_tests()

