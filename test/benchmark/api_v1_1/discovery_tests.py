from config.api1_1_config import *
from config.amqp import *
from modules.logger import Log

from proboscis import test

LOG = Log(__name__)

@test(groups=['benchmark.discovery'])
class BenchmarkDiscoveryTests(object):
    def __init__(self):
        self.__testname = 'discovery'
        pass

    @test(groups=['discovery.pre.tests'])
    def test_check_precondition(self):
        """ Testing discovery precondition fulfilled """
        pass
