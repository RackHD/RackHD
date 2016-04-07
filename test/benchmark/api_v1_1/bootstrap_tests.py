from config.api1_1_config import *
from config.amqp import *
from modules.logger import Log

from proboscis import test
LOG = Log(__name__)

@test(groups=['benchmark.bootstrap'])
class BenchmarkBootstrapTests(object):
    def __init__(self):
        self.__testname = 'bootstrap'
        pass

    @test(groups=['bootstrap.pre.tests'])
    def test_check_precondition(self):
        """ Testing bootstrap precondition fulfilled """
        pass

