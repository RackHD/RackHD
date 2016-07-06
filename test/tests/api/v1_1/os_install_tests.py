from config.api1_1_config import *
from config.settings import *
from modules.logger import Log
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import rest
from workflows_tests import WorkflowsTests as workflows
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis import SkipTest
from proboscis import test
from proboscis import after_class
from proboscis import before_class
from json import dumps, loads
import os

LOG = Log(__name__)
DEFAULT_TIMEOUT = 5400
ENABLE_FORMAT_DRIVE=False
if os.getenv('RACKHD_ENABLE_FORMAT_DRIVE', 'false') == 'true': 
    ENABLE_FORMAT_DRIVE=True

@test(groups=['os-install.v1.1.tests'], \
    depends_on_groups=['amqp.tests'])
class OSInstallTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__base = defaults.get('RACKHD_BASE_REPO_URL', \
            'http://{0}:{1}'.format(HOST_IP, HOST_PORT))
        self.__obm_options = { 
            'obmServiceName': defaults.get('RACKHD_GLOBAL_OBM_SERVICE_NAME', \
                'ipmi-obm-service')
        }
            
    @before_class()
    def setup(self):
        pass
        
    @after_class(always_run=True)
    def teardown(self):
        self.__format_drives()  
    
    def __get_data(self):
        return loads(self.__client.last_response.data)
    
    def __post_workflow(self, graph_name, nodes, body):
        workflows().post_workflows(graph_name, timeout_sec=DEFAULT_TIMEOUT, nodes=nodes, data=body)         

    def __format_drives(self):
        # Clear disk MBR and partitions
        command = 'for disk in `lsblk | grep disk | awk \'{print $1}\'`; do '
        command = command + 'sudo dd if=/dev/zero of=/dev/$disk bs=512 count=1 ; done'
        body = {
            'options': {
                'shell-commands': {
                    'commands': [ 
                        { 'command': command } 
                    ]
                },
                'set-boot-pxe': self.__obm_options,
                'reboot-start': self.__obm_options,
                'reboot-end': self.__obm_options
            }
        }
        self.__post_workflow('Graph.ShellCommands', [], body) 

    @test(enabled=ENABLE_FORMAT_DRIVE, groups=['format-drives.v1.1.test'])
    def test_format_drives(self):
        """ Drive Format Test """
        self.__format_drives()  
        
    def install_centos(self, version, nodes=[], options=None):
        graph_name = 'Graph.InstallCentOS'
        os_repo = defaults.get('RACKHD_CENTOS_REPO_PATH', \
            self.__base + '/repo/centos/{0}'.format(version))
        body = options
        if body == None:
            body = {
                'options': {
                    'defaults': {
                        'installDisk': '/dev/sda',
                        'kvm': 'undefined', 
                        'version': version,
                        'repo': os_repo
                    },
                    'set-boot-pxe': self.__obm_options,
                    'reboot': self.__obm_options,
                    'install-os': {
                        'schedulerOverrides': {
                            'timeout': 3600000
                        }
                    }
                }
            } 
        self.__post_workflow(graph_name, nodes, body)
        
    def install_esxi(self, version, nodes=[], options=None):
        graph_name = 'Graph.InstallEsx'
        os_repo = defaults.get('RACKHD_ESXI_REPO_PATH', \
            self.__base + '/repo/esxi/{0}'.format(version))
        body = options
        if body == None:
            body = {
                'options': {
                    'defaults': {
                        'installDisk': 'firstdisk',
                        'version': version, 
                        'repo': os_repo,
                        'users': [{ 'name': 'onrack', 'password': 'Onr@ck1!', 'uid': 1010 }]
                    },
                    'set-boot-pxe': self.__obm_options,
                    'reboot': self.__obm_options,
                    'install-os': {
                        'schedulerOverrides': {
                            'timeout': 3600000
                        }
                    }
                }
            }
        self.__post_workflow(graph_name, nodes, body)  
        
    def install_suse(self, version, nodes=[], options=None):
        graph_name = 'Graph.InstallSUSE'
        os_repo = defaults.get('RACKHD_SUSE_REPO_PATH', \
            self.__base + '/repo/suse/{0}/'.format(version))
        body = options
        if body == None:
            body = {
                'options': {
                    'defaults': {
                        'installDisk': '/dev/sda',
                        'kvm': 'undefined', 
                        'version': version,
                        'repo': os_repo
                    },
                    'set-boot-pxe': self.__obm_options,
                    'reboot': self.__obm_options,
                    'install-os': {
                        'schedulerOverrides': {
                            'timeout': 3600000
                        }
                    }
                }
            }
        self.__post_workflow(graph_name, nodes, body)
        
    def install_ubuntu(self, version, nodes=[], options=None):
        graph_name = 'Graph.InstallUbuntu'
        os_repo = defaults.get('RACKHD_UBUNTU_REPO_PATH', \
            self.__base + '/repo/ubuntu')
        body = options
        if body == None:
            body = {
                'options': {
                    'defaults': {
                        'installDisk': '/dev/sda',
                        'kvm': 'undefined', 
                        'version': version,
                        'repo': os_repo
                    },
                    'set-boot-pxe': self.__obm_options,
                    'reboot': self.__obm_options,
                    'install-ubuntu': {
                        'schedulerOverrides': {
                            'timeout': 3600000
                        }
                    }
                }
            }
        self.__post_workflow(graph_name, nodes, body)

    @test(enabled=True, groups=['centos-6-5-install.v1.1.test'])
    def test_install_centos_6(self):
        """ Testing CentOS 6.5 Installer Workflow """
        self.install_centos('6.5')
        
    @test(enabled=True, groups=['centos-7-install.v1.1.test'])
    def test_install_centos_7(self, nodes=[], options=None):
        """ Testing CentOS 7 Installer Workflow """
        self.install_centos('7.0')

    @test(enabled=True, groups=['ubuntu-install.v1.1.test'])
    def test_install_ubuntu(self, nodes=[], options=None):
        """ Testing Ubuntu 14.04 Installer Workflow """
        self.install_ubuntu('trusty')
        
    @test(enabled=True, groups=['suse-install.v1.1.test'])
    def test_install_suse(self, nodes=[], options=None):
        """ Testing OpenSuse Leap 42.1 Installer Workflow """
        self.install_suse('42.1')
        
    @test(enabled=True, groups=['esxi-5-5-install.v1.1.test'])
    def test_install_esxi_5_5(self, nodes=[], options=None):
        """ Testing ESXi 5.5 Installer Workflow """
        self.install_esxi('5.5')
        
    @test(enabled=True, groups=['esxi-6-install.v1.1.test'])
    def test_install_esxi_6(self, nodes=[], options=None):
        """ Testing ESXi 6 Installer Workflow """
        self.install_esxi('6.0')
