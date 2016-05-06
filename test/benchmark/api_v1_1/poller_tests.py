from modules.logger import Log
import time

from proboscis.asserts import assert_equal
from proboscis import SkipTest
from proboscis import test
from json import loads

from benchmark import ansible_ctl
from benchmark.utils import parser
from benchmark.utils.case_recorder import caseRecorder


LOG = Log(__name__)

@test(groups=['benchmark.poller'])
class BenchmarkPollerTests(object):
    def __init__(self):
        self.__testname = 'poller'
        ansible_ctl.render_case_name(self.__testname)
        self.__data_path = ansible_ctl.get_data_path_per_case()
        self.__case_recorder = caseRecorder(self.__data_path)

    @test(groups=['test-poller'], depends_on_groups=['test-node-poller'])
    def test_runtime(self):
        """ Testing footprint scenario: poller """
        self.__case_recorder.write_interval(ansible_ctl.get_data_interval())
        self.__case_recorder.write_start()

        assert_equal(True, ansible_ctl.start_daemon(), \
                    message='Failed to start data collection daemon!')

        # Run test scenario
        # In this case, wait for 15 mins to let RackHD run pollers
        LOG.info('Start test case...')
        time.sleep(900)
        LOG.info('End test case. Fetch log...')

        assert_equal(True, ansible_ctl.collect_data(), message='Failed to collect footprint data!')
        self.__case_recorder.write_end()

        LOG.info('Parse log and generate html reports')
        try:
            parser.parse(self.__data_path)
        except RuntimeError as err:
            LOG.warning('Error on parsing log or generating reports: ')
            LOG.warning(err)
