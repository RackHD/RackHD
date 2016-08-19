from benchmark.utils.ansible_control import ansibleControl
from benchmark.utils.case_recorder import caseRecorder
from benchmark.utils import parser

class manipulator(object):
    """
    Class for controlling benchmark data collection process independently
    without running any benchmark test cases
    """
    def __init__(self):
        self._ansible_ctl = ansibleControl()

    def start(self):
        self._ansible_ctl.render_case_name('manual')
        self._ansible_ctl.setup_env()
        case_recorder = caseRecorder(self._ansible_ctl.get_data_path_per_case())
        case_recorder.write_interval(self._ansible_ctl.get_data_interval())
        case_recorder.write_start()
        self._ansible_ctl.start_daemon()

    def stop(self):
        case_recorder = caseRecorder(self._ansible_ctl.get_data_path_per_case())
        self._ansible_ctl.collect_data()
        case_recorder.write_end()
        parser.parse(self._ansible_ctl.get_data_path_per_case())

    def get_data_path(self):
        return self._ansible_ctl.get_data_path_per_case()

