import os
import time
import json

from modules.logger import Log

from config.benchmark_config import *
from ansible.playbook import PlayBook
from ansible.inventory import Inventory
from ansible import callbacks
from ansible import utils
from ansible import constants

import jinja2
from tempfile import NamedTemporaryFile

LOG = Log(__name__)

"""
Class to abstract ansible operations
"""
class ansibleControl(object):
    def __init__(self):
        self.__var_file = os.path.dirname(__file__) + '/ansible/group_vars/benchmark.json'
        self.__config_data_path = 'test_machine_log_path'
        self.__config_case_name = 'test_case_name'
        self.__config_interval = 'data_interval'

        self.__set_data_path()
        self.__set_host_port()
        self.__hosts = self.__get_hosts()

    def __set_data_path(self):
        # Get current time as the name of log directory
        timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time()))

        # Get path name
        path = self.__get_varfile_variable(self.__config_data_path)

        # Modify new paht name
        insert_index = path.find('benchmark') + len('benchmark')
        path = path[0:insert_index] + '/' + timestamp

        # Write back to json file
        return self.__render_varfile_variable(self.__config_data_path, path)

    def __set_host_port(self):
        return self.__render_varfile_variable("host_port", HOST_PORT)

    def __get_hosts(self):
        # Overwrite remote temp file incase ansible doesn't have right to default path
        constants.DEFAULT_REMOTE_TMP = '/tmp'

        # Disable host key checking incase RackHD is not in known_hosts
        constants.HOST_KEY_CHECKING = False

        # Dynamic Inventory
        inventory = """
            [test_machine]
            localhost   ansible_connection=local

            [rackhd]
            {{ rackhd_ip_address }}:{{ rackhd_ssh_port }}

            [test_machine:vars]
            ansible_sudo_pass={{ local_pwd }}

            [rackhd:vars]
            ansible_connection=ssh
            ansible_ssh_user={{ rackhd_ssh_user }}
            ansible_ssh_pass={{ rackhd_ssh_pwd }}
            ansible_sudo_pass={{ rackhd_ssh_pwd }}

            [benchmark:children]
            test_machine
            rackhd
        """

        local_usr, local_pw, rackhd_pt, rackhd_usr, rackhd_pw = get_ansible_auth()

        inventory_template = jinja2.Template(inventory)
        rendered_inventory = inventory_template.render({
            'local_pwd': local_pw,
            'rackhd_ip_address': HOST_IP,
            'rackhd_ssh_port': rackhd_pt,
            'rackhd_ssh_user': rackhd_usr,
            'rackhd_ssh_pwd': rackhd_pw,
            'rackhd_sudo_pwd': rackhd_pw
        })

        # Create a temporary file and write the template string to it
        hosts = NamedTemporaryFile(delete=False)
        hosts.write(rendered_inventory)
        hosts.close()

        return hosts

    def __del__(self):
        os.remove(self.__hosts.name)

    def __check_success(self, stats):
        succeed = True
        hosts = stats.processed.keys()

        for h in hosts:
            t = stats.summarize(h)

            if t['failures'] > 0 or t['unreachable'] > 0:
                succeed = False

        return succeed

    def __render_varfile_variable(self, key, value):

        with open(self.__var_file, 'r+') as f:
            # Load json data
            json_data = json.load(f)

            # Change the case name
            json_data[key] = value

            # Write json data back to the var file
            f.seek(0)
            f.write(json.dumps(json_data, indent=4, separators=(',', ': ')))
            f.truncate()
            f.close()


    def __get_varfile_variable(self, key):

        value = ""

        with open(self.__var_file, 'r') as f:
            json_data = json.load(f)
            value = json_data[key]

        return value

    def __run_playbook(self, name):
        # Boilerplace callbacks for stdout/stderr and log output
        utils.VERBOSITY = 0
        playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
        stats = callbacks.AggregateStats()
        runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)

        # load playbook
        pb = PlayBook(
            playbook = os.path.dirname(__file__) + '/ansible/' + name,
            host_list = self.__hosts.name,
            callbacks=playbook_cb,
            runner_callbacks=runner_cb,
            stats=stats
        )

        pb.run()

        return self.__check_success(pb.stats)

    def setup_env(self):
        return self.__run_playbook('setup_env.yml')

    def start_daemon(self):
        return self.__run_playbook('start_daemon.yml')

    def collect_data(self):
        return self.__run_playbook('collect_data.yml')

    def render_case_name(self, name):
        return self.__render_varfile_variable(self.__config_case_name, name)

    def get_data_path_per_case(self):
        path = self.__get_varfile_variable(self.__config_data_path) + '/' + \
               self.__get_varfile_variable(self.__config_case_name)

        path = path.replace('{{ lookup(\'env\', \'HOME\') }}', '~')
        return os.path.expanduser(str(path))

    def render_data_interval(self, interval):
        return self.__render_varfile_variable(self.__config_interval, interval)

    def get_data_interval(self):
        return self.__get_varfile_variable(self.__config_interval)
