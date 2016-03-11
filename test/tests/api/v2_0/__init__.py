# import tests
from config_tests import ConfigTests
from nodes_tests import NodesTests
from catalogs_tests import CatalogsTests
from pollers_tests import PollersTests
from obm_tests import OBMTests

tests = [
    'nodes_api2.tests',
    'config_api2.tests',
    'catalogs_api2.tests',
    'pollers.tests',
    'obm_api2.tests'
]
