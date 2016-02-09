# import tests
from chassis_tests import ChassisTests 
from systems_tests import SystemsTests 
from task_service_tests import TaskServiceTests

tests = [
    'redfish.chassis.tests',
    'redfish.systems.tests',
    'redfish.task_service.tests'
]
