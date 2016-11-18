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
from proboscis.asserts import fail
from json import dumps, loads, load
from collections import Mapping
import os

LOG = Log(__name__)
DEFAULT_TIMEOUT_SEC = 5400
ENABLE_FORMAT_DRIVE=False
if os.getenv('RACKHD_ENABLE_FORMAT_DRIVE', 'false') == 'true':
    ENABLE_FORMAT_DRIVE=True
IS_EMC = defaults.get('RACKHD_REDFISH_EMC_OEM', False)

@test(groups=['os-install.v1.1.tests'], depends_on_groups=['obm.tests'])
class OSInstallTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__base = defaults.get('RACKHD_BASE_REPO_URL', \
            'http://{0}:{1}'.format(HOST_IP, HOST_PORT))
        self.__obm_options = {
            'obmServiceName': defaults.get('RACKHD_GLOBAL_OBM_SERVICE_NAME', \
                'ipmi-obm-service')
        }
        if self.__obm_options['obmServiceName'] == 'redfish-obm-service':
            self.__obm_options['force'] = 'true'
        self.__sampleDir = defaults.get('RACKHD_SAMPLE_PAYLOADS_PATH', '../example/samples/')

    @before_class()
    def setup(self):
        pass

    @after_class(always_run=True)
    def teardown(self):
        self.__format_drives()

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __post_workflow(self, graph_name, nodes, body):
        workflows().post_workflows(graph_name, timeout_sec=DEFAULT_TIMEOUT_SEC, nodes=nodes, data=body)

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

    def __get_os_install_payload(self, payload_file_name):

        payload = open(self.__sampleDir  + payload_file_name, 'r')
        body = load(payload)
        payload.close()
        return body

    def __update_body(self, body, updates):
        #check each key, value pair in the updates
        for key, value in updates.iteritems():
            #if value is a dict, recursivly call __update_body
            if isinstance(value, Mapping):

                r = self.__update_body(body.get(key, {}), value)
                body[key] = r
            elif isinstance(value, list) and key in body.keys():
                body[key] = body[key] + updates[key]
            else:
                body[key] = updates[key]
        return body

    def __test_link_up(self, network_devices):
        for entry in network_devices:
            if entry['ipv4'] != None:
                hostname = entry['ipv4']['ipAddr']
                response = os.system('ping -c 1 ' + hostname)
                assert_equal(response, 0, message='link {0} device {1} is down'.format(entry['device'], hostname))

    @test(enabled=ENABLE_FORMAT_DRIVE, groups=['format-drives.v1.1.test'])
    def test_format_drives(self):
        """ Drive Format Test """
        self.__format_drives()

    def install_centos(self, version, nodes=[], options=None, payloadFile=None):
        graph_name = 'Graph.InstallCentOS'
        os_repo = defaults.get('RACKHD_CENTOS_REPO_PATH', \
            self.__base + '/repo/centos/{0}'.format(version))

        # load the payload from the specified file
        if payloadFile != None:
            body = self.__get_os_install_payload(payloadFile)
        else:
            body = {}

        # if no options are specified, fill in the minimum required options
        if options == None:
            options = {
                'options': {
                    'defaults': {
                        'repo': os_repo
                    }
                }
            }

        # add additional options to the body
        self.__update_body(body, options);

        # run the workflow
        self.__post_workflow(graph_name, nodes, body)

        #test network devices
        if 'networkDevices' in body['options']['defaults']:
            self.__test_link_up(body['options']['defaults']['networkDevices'])

    def install_esxi(self, version, nodes=[], options=None, payloadFile=None):
        graph_name = 'Graph.InstallESXi'
        os_repo = defaults.get('RACKHD_ESXI_REPO_PATH', \
            self.__base + '/repo/esxi/{0}'.format(version))
        # load the payload from the specified file
        if payloadFile != None:
            body = self.__get_os_install_payload(payloadFile)
        else:
            body = {}
        # if no options are specified, fill in the minimum required options
        if options == None:
            options = {
                'options':{
                    'defaults':{
                        'installDisk': 'firstdisk',
                        'version': version,
                        'repo': os_repo
                    },
                    'set-boot-pxe': self.__obm_options,
                    'reboot': self.__obm_options,
                    'install-os': {
                        '_taskTimeout': 3600000
                    }
                }
            }
        # add additional options to the body
        self.__update_body(body, options)

        if self.__obm_options['obmServiceName'] == 'redfish-obm-service' and IS_EMC:
            body['options']['install-os']['kargs'] = {'acpi':'off'}

        self.__post_workflow(graph_name, nodes, body)

        if 'networkDevices' in body['options']['defaults']:
            self.__test_link_up(body['options']['defaults']['networkDevices'])


    def install_suse(self, version, nodes=[], options=None, payloadFile=None):
        graph_name = 'Graph.InstallSUSE'
        os_repo = defaults.get('RACKHD_SUSE_REPO_PATH', \
            self.__base + '/repo/suse/{0}/'.format(version))

        # load the payload from the specified file
        if payloadFile != None:
            body = self.__get_os_install_payload(payloadFile)
        else:
            body = {}

        if options == None:
            options = {
                'options': {
                    'defaults': {
                        'version': version,
                        'repo': os_repo,
                        'kargs' : {'NetWait': '10'}
                    }
                }
            }

        # add additional options to the body
        self.__update_body(body, options);
        # run the workflow
        self.__post_workflow(graph_name, nodes, body)

    def install_ubuntu(self, version, payloadFile, nodes = []):
        graph_name = 'Graph.InstallUbuntu'
        os_repo = defaults.get('RACKHD_UBUNTU_REPO_PATH', \
            self.__base + '/repo/ubuntu')
        # load the payload from the specified file
        body = {}
        body = self.__get_os_install_payload(payloadFile)
        extra_options = {
            'options':{
                'defaults':{
                    'repo': os_repo ,
                    'kargs':{
                        'live-installer/net-image': os_repo + '/install/filesystem.squashfs'
                    }
                },
                'set-boot-pxe': self.__obm_options,
                'reboot': self.__obm_options,
                'install-ubuntu': {
                    '_taskTimeout': 3600000
                }
            }
        }
        self.__update_body(body, extra_options)
        self.__post_workflow(graph_name, nodes, body)

        #test network devices
        if 'networkDevices' in body['options']['defaults']:
            self.__test_link_up(body['options']['defaults']['networkDevices'])

    def install_windowsServer2012(self, version, payloadFile, nodes=[]):
        graph_name = 'Graph.InstallWindowsServer'
        os_repo = defaults.get('RACKHD_SMB_WINDOWS_REPO_PATH', None)
        if None == os_repo:
            fail('user must set RACKHD_SMB_WINDOWS_REPO_PATH')
        # load the payload from the specified file
        body = {}

        body = self.__get_os_install_payload(payloadFile)

        # The value of the productkey below is not a valid product key. It is a KMS client
        # key that was generated to run the workflows without requiring a real product key.
        # This key is available to public on the Microsoft site.
        extra_options = {
                'options': {
                    'defaults': {
                        'productkey': 'D2N9P-3P6X9-2R39C-7RTCD-MDVJX',
                        'smbUser':  defaults.get('RACKHD_SMB_USER' , 'onrack'),
                        'smbPassword':  defaults.get('RACKHD_SMB_PASSWORD' , 'onrack'),
                        'smbRepo': os_repo,
                        'repo' : defaults.get('RACKHD_WINPE_REPO_PATH',  \
                            self.__base + '/repo/winpe')
                    }
                }
        }
        self.__update_body(body, extra_options)
        new_body = dumps(body)
        self.__post_workflow(graph_name, nodes, body)

        if 'networkDevices' in body['options']['defaults']:
            self.__test_link_up(body['options']['defaults']['networkDevices'])

    def install_coreos(self, payloadFile, nodes=[], options=None):
        graph_name = 'Graph.InstallCoreOS'
        os_repo = defaults.get('RACKHD_COREOS_REPO_PATH', \
            self.__base + '/repo/coreos')
        if options == None:

            options = {
                'options': {
                    'defaults': {
                        'repo': os_repo
                    }
                }
            }
        if(payloadFile):
            body = self.__get_os_install_payload(payloadFile)
        else:
            body = self.__get_os_install_payload('install_coreos_payload_minimum.json')

        self.__update_body(body, options)
        self.__post_workflow(graph_name, nodes, body)

    @test(enabled=True, groups=['centos-6-5-install.v1.1.test'])
    def test_install_centos_6(self, nodes=[], options=None):
        """ Testing CentOS 6.5 Installer Workflow """
        options = {
            'options': {
                'defaults': {
                    'installDisk': '/dev/sda',
                    'version': '6.5',
                    'repo': defaults.get('RACKHD_CENTOS_REPO_PATH', \
                        self.__base + '/repo/centos/6.5'),
                    'users': [{'name': 'onrack', 'password': 'Onr@ck1!', 'uid': 1010}]
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

        self.install_centos('6.5')

    @test(enabled=True, groups=['centos-7-install.v1.1.test'])
    def test_install_centos_7(self, nodes=[], options=None):
        """ Testing CentOS 7 Installer Workflow """
        options = {
            'options': {
                'defaults': {
                    'installDisk': '/dev/sda',
                    'version': '7.0',
                    'repo': defaults.get('RACKHD_CENTOS_REPO_PATH', \
                        self.__base + '/repo/centos/7.0'),
                    'users': [{'name': 'onrack', 'password': 'Onr@ck1!', 'uid': 1010}]
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
        self.install_centos('7.0', options=options)

    @test(enabled=True, groups=['ubuntu-minimal-install.v1.1.test'])
    def test_install_min_ubuntu(self, nodes=[], options=None):
        """ Testing Ubuntu 14.04 Installer Workflow With Minimal Payload """
        self.install_ubuntu('trusty', 'install_ubuntu_payload_iso_minimal.json')

    @test(enabled=True, groups=['ubuntu-maximal-install.v1.1.test'])
    def test_install_max_ubuntu(self, nodes=[], options=None):
        """ Testing Ubuntu 14.04 Installer Workflow With Maximal Payload """
        self.install_ubuntu('trusty', 'install_ubuntu_payload_iso_full.json')

    @test(enabled=True, groups=['suse-minimal-install.v1.1.test'])
    def test_install_suse_min(self, nodes=[], options=None):
        """ Testing OpenSuse Leap 42.1 Installer Workflow With Min Payload"""
        self.install_suse('42.1', payloadFile='install_suse_payload_minimal.json')

    @test(enabled=True, groups=['suse-full-install.v1.1.test'])
    def test_install_suse_max(self, nodes=[], options=None):
        """ Testing OpenSuse Leap 42.1 Installer Workflow With Max Payload"""
        self.install_suse('42.1', payloadFile='install_suse_payload_full.json')

    @test(enabled=True, groups=['esxi-5-5-min-install.v1.1.test'])
    def test_install_min_esxi_5_5(self, nodes=[], options=None):
        """ Testing  ESXi 5.5 Installer Workflow With Minimal Payload """
        self.install_esxi('5.5', payloadFile='install_esx_payload_minimal.json')

    @test(enabled=True, groups=['esxi-5-5-max-install.v1.1.test'])
    def test_install_max_esxi_5_5(self, nodes=[], options=None):
        """ Testing  ESXi 5.5 Installer Workflow With Maximum Payload """
        self.install_esxi('5.5', payloadFile='install_esx_payload_full.json')

    @test(enabled=True, groups=['esxi-6-min-install.v1.1.test'])
    def test_install_min_esxi_6(self, nodes=[], options=None):
        """ Testing  ESXi 6 Installer Workflow With Minimal Payload """
        self.install_esxi('6.0', payloadFile='install_esx_payload_minimal.json')

    @test(enabled=True, groups=['esxi-6-max-install.v1.1.test'])
    def test_install_max_esxi_6(self, nodes=[], options=None):
        """ Testing  ESXi 6 Installer Workflow With Maximum Payload """
        self.install_esxi('6.0', payloadFile='install_esx_payload_full.json')

    @test(enabled=True, groups=['windowsServer2012-maximum-install.v1.1.test'])
    def test_install_max_windowsServer2012(self, nodes=[], options=None):
        """ Testing Windows Server 2012 Installer Workflow with Max payload"""
        self.install_windowsServer2012('10.40','install_windows_payload_full.json')

    @test(enabled=True, groups=['windowsServer2012-minimum-install.v1.1.test'])
    def test_install_min_windowsServer2012(self, nodes=[], options=None):
        """ Testing Windows Server 2012 Installer Workflow with Min payload"""
        self.install_windowsServer2012('10.40','install_windows_payload_minimal.json')

    @test(enabled=True, groups=['coreos-minimum-install.v1.1.test'])
    def test_install_coreos_min(self, nodes=[]):
        """ Testing CoreOS Installer Workflow with Minimum Payload"""
        self.install_coreos(payloadFile='install_coreos_payload_minimum.json')

    @test(enabled=True, groups=['coreos-full-install.v1.1.test'])
    def test_install_coreos_full(self, nodes=[] ):
        """ Testing CoreOS Installer Workflow with Full Payload"""
        self.install_coreos(payloadFile='install_coreos_payload_full.json')

    @test(enabled=True, groups=['centos-6-5-minimal-install.v1.1.test'])
    def test_install_centos_6_minimal(self):
        """ Testing CentOS 6.5 Installer Workflow """
        self.install_centos('6.5', payloadFile='install_centos_6_payload_minimal.json')

    @test(enabled=True, groups=['centos-6-5-full-install.v1.1.test'])
    def test_install_centos_6_full(self, nodes=[], options=None):
        """ Testing CentOS 6.5 Installer Workflow """
        self.install_centos('6.5', payloadFile='install_centos_6_payload_full.json')

    @test(enabled=True, groups=['centos-7-minimal-install.v1.1.test'])
    def test_install_centos_7_minimal(self, nodes=[], options=None):
        """ Testing CentOS 7 Installer Workflow """
        self.install_centos('7.0', payloadFile='install_centos_7_payload_minimal.json')

    @test(enabled=True, groups=['centos-7-full-install.v1.1.test'])
    def test_install_centos_7_full(self, nodes=[], options=None):
        """ Testing CentOS 7 Installer Workflow """
        self.install_centos('7.0', payloadFile='install_centos_7_payload_full.json')
