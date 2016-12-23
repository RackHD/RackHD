'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

OnRack/RackHD Functional Integration Test (FIT) library
This is the main common function library for OnRack/RackHD FIT tests.
'''

# Standard imports
import os
import sys
import json
import subprocess
import time, datetime
import unittest
import signal
import re
import requests
import pexpect
import shutil
import inspect

import nose
import argparse
from flogging import get_loggers, logger_config_api
from mkcfg import mkcfg

sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test")

VERBOSITY = int(os.getenv("VERBOSITY", "1"))
# The global "VERBOSITY" will go away once all usages are removed. At that point,
# the following call can migrate some place that makes more sense (not sure where
# that is yet!)

ARGS_LIST = {}
GLOBAL_CONFIG = {}
STACK_CONFIG = {}
TEST_PATH = None
CONFIG_PATH = None
API_PORT = "None"
API_PROTOCOL = "None"
AUTH_TOKEN = "None"
REDFISH_TOKEN = "None"
BMC_LIST = []

def cfg():
    """
    returns the configuration dictionary
    :return: dictionary of current config
    """
    return mkcfg().get()

def compose_global_config():
    """
    creates a configuration using the global_config.json file.
    this is the old method for generating configurations but
    is still being used.  Will be phased out eventually.
    :return: None
    """
    global ARGS_LIST
    global GLOBAL_CONFIG
    global STACK_CONFIG
    global TEST_PATH
    global CONFIG_PATH
    global API_PORT
    global API_PROTOCOL
    global VERBOSITY

    # Pull arguments from environment into ARGS_LIST
    ARGS_LIST = \
        {
        "v": os.getenv("VERBOSITY", "0"),
        "config":  os.getenv("CONFIG", "config"),
        "stack": os.getenv("STACK", "None"), # Stack label
        "ora": os.getenv("ORA", "localhost"), # Appliance IP or hostname
        "bmc": "None", # BMC IP or hostname
        "sku": os.getenv("SKU", "all"), # node SKU name
        "obmmac": os.getenv("OBMMAC", "all"), # node OBM MAC address
        "nodeid": os.getenv("NODEID", "None"), # node ID
        "hyper": "None", # hypervisor address
        "version": os.getenv("VERSION", "onrack-devel"), # code version
        "template": os.getenv("TEMPLATE", "None"), # path or URL link to OVA for deployment
        "xunit": os.getenv("XUNIT", False), # XUNIT output
        "numvms" : os.getenv("NUMVMS", 1), # number of OVA for deployment
        "list": os.getenv("LIST", False), # list tests
        "group": os.getenv("GROUP", "all"), # test group
        "http": os.getenv("HTTP", "False"), # force http api protocol
        "https": os.getenv("HTTPS", "False"), # force https api protocol
        "port": os.getenv("PORT", "None") # port number override
    }

    # transfer argparse args to ARGS_LIST
    for key in cfg()['cmd-args-list']:
        ARGS_LIST[key] = cfg()['cmd-args-list'][key]

    # Get top level path via git
    TEST_PATH = subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/"
    CONFIG_PATH = TEST_PATH + ARGS_LIST["config"] + "/"
    if ARGS_LIST["config"] != 'config':
        print "*** Using config file path:", ARGS_LIST["config"]
    VERBOSITY = int(os.getenv("VERBOSITY", "1"))
    # The global "VERBOSITY" will go away once all usages are removed. At that point,
    # the following call can migrate some place that makes more sense (not sure where
    # that is yet!)

    # Global Config files
    try:
        GLOBAL_CONFIG = json.loads(open(CONFIG_PATH + "global_config.json").read())
    except:
        print "**** Global Config file: " + CONFIG_PATH + "global_config.json" + " missing or corrupted! Exiting...."
        sys.exit(255)
    try:
        STACK_CONFIG = json.loads(open(CONFIG_PATH + "stack_config.json").read())
    except:
        print "**** Stack Config file:" + CONFIG_PATH + "stack_config.json" + " missing or corrupted! Creating empty stack file...."
        STACK_CONFIG = []

    # apply stack detail files from config dir to STACK_CONFIG dict
    for entry in os.listdir(CONFIG_PATH):
        if entry != "global_config.json" and entry != "stack_config.json" and ".json" in entry:
            try:
                detailfile = json.loads(open(CONFIG_PATH + entry).read())
            except:
                print "**** Invalid JSON file:", CONFIG_PATH + entry
            else:
                STACK_CONFIG.update(detailfile)


    # This section derives default stack configuration data from STACK-CONFIG, use environment to override
    ARGS_LIST.update(
        {
            "usr": GLOBAL_CONFIG['credentials']['ora'][0]['username'],
            "pwd": GLOBAL_CONFIG['credentials']['ora'][0]['password']
        }
    )

    if ARGS_LIST["stack"] != "None":
        if ARGS_LIST["stack"] not in STACK_CONFIG:
            print "**** Stack {0} not found in stack config file {1}.  Exiting....".format(ARGS_LIST["stack"], CONFIG_PATH + "stack_config.json")
            sys.exit(255)
        if "ora" in STACK_CONFIG[ARGS_LIST["stack"]]:
            ARGS_LIST["ora"] = STACK_CONFIG[ARGS_LIST["stack"]]['ora']
        else:
            ARGS_LIST["ora"] = "localhost"
        if "bmc" in STACK_CONFIG[ARGS_LIST["stack"]]:
            ARGS_LIST["bmc"] = STACK_CONFIG[ARGS_LIST["stack"]]['bmc']
        if "hyper" in STACK_CONFIG[ARGS_LIST["stack"]]:
            ARGS_LIST["hyper"] = STACK_CONFIG[ARGS_LIST["stack"]]['hyper']

    # set api port and protocol from command line
    if ARGS_LIST['port'] != "None":
        API_PORT = ARGS_LIST['port']
    if ARGS_LIST['http'] == "True":
        API_PROTOCOL = "http"
        if API_PORT == "None":
            API_PORT = GLOBAL_CONFIG['ports']['http']
    if ARGS_LIST['https'] == "True":
        API_PROTOCOL = "https"
        if API_PORT == "None":
            API_PORT = GLOBAL_CONFIG['ports']['https']
    if ARGS_LIST["ora"] == "localhost":
        if API_PROTOCOL == "None":
            API_PROTOCOL = 'http'
        if API_PORT == "None":
            API_PORT = '8080'
    # set OVA template from command line
    if ARGS_LIST["template"] == "None":
        ARGS_LIST["template"] = GLOBAL_CONFIG['repos']['install']['template']

def compose_config(use_sysargs=False):
    """
    creates a configuration based on
    :param use_sysargs: set to true if sys.argv is to be processed.
    :return: None
    """
    args_list = {}
    if use_sysargs:
        # Args from command line
        args_list['cmd-args-list'] = mkargs()
        config = args_list['cmd-args-list']['config']
        cfg = mkcfg(config)
    else:
        # Args from default set
        no_args = {}
        args_list['cmd-args-list'] = mkargs(no_args)
        cfg = mkcfg()

    if cfg.get_path() is None:

        # How to build a configuration:
        #
        # 1. Start with the default config json file composition.
        # 2. Add stack overlay
        # 3. Add cmd line args
        # 4. Process any overrides from the command line.
        # 5. Save (generate) the configuration to a file
        #
        default_composition = ['rackhd_default.json',
                               'credentials_default.json',
                               'install_default.json',
                               'cit_default.json']

        # config file composition
        cfg.add_from_file_list(default_composition)

        # stack overlay configuration
        stack = args_list['cmd-args-list']['stack']
        if stack is not None:
            cfg.add_from_file("stack_config.json", stack)

        # add the args_list
        cfg.add_from_dict(args_list)

        # save
        args = args_list['cmd-args-list']
        cfg.add_from_dict({
            'env': {
                'VERBOSITY':  str(args['v']),
                'ORA':  str(args['ora']),
                'STACK':  str(args['stack']),
                'SKU':  str(args['sku']) ,
                'NODEID':  str(args['nodeid']),
                'OBMMAC':  str(args['obmmac']),
                'VERSION':  str(args['version']),
                'TEMPLATE':  str(args['template']),
                'XUNIT':  str(args['xunit']),
                'NUMVMS':  str(args['numvms']),
                'GROUP':  str(args['group']),
                'CONFIG':  str(args['config']),
                'HTTP':  str(args['http']),
                'HTTPS':  str(args['https']),
                'PORT':  str(args['port']),
                'PATH':  os.environ['PATH']
            }
        })

        # generate the configuration file
        cfg.generate()
        print "*** Using config file: {0}".format(cfg.get_path())

def mkargs(in_args=None):
    """
    processes the command line options as passed in by in_args.
    :param in_args: input arguments
    :return: dictionary of processed arguments
    """
    if in_args is None:
        in_args = sys.argv[1:]

    # command line argument parser returns cmd_args dict
    arg_parser = argparse.ArgumentParser(description="Command Help")
    arg_parser.add_argument("-test", default="tests/",
                            help="test to execute, default: tests/")
    arg_parser.add_argument("-config", default="config",
                            help="config file location, default: config")
    arg_parser.add_argument("-group", default="all",
                            help="test group to execute: 'smoke', 'regression', 'extended', default: 'all'")
    arg_parser.add_argument("-stack", default=None,
                            help="stack label (test bed), overrides -ora")
    arg_parser.add_argument("-ora", default="localhost",
                            help="OnRack/RackHD appliance IP address or hostname, default: localhost")
    arg_parser.add_argument("-version", default="onrack-devel",
                            help="OnRack package install version, example:onrack-release-0.3.0, default: onrack-devel")
    arg_parser.add_argument("-template", default=None,
                            help="path or URL link to OVA template or OnRack OVA")
    arg_parser.add_argument("-xunit", default="False", action="store_true",
                            help="generates xUnit XML report files")
    arg_parser.add_argument("-numvms", default=1, type=int,
                            help="number of virtual machines for deployment on specified stack")
    arg_parser.add_argument("-list", default="False", action="store_true",
                            help="generates test list only")
    arg_parser.add_argument("-sku", default="all",
                            help="node SKU, example:Phoenix, default=all")
    group = arg_parser.add_mutually_exclusive_group(required=False)
    group.add_argument("-obmmac", default="all",
                       help="node OBM MAC address, example:00:1e:67:b1:d5:64")
    group.add_argument("-nodeid", default="None",
                       help="node identifier string of a discovered node, example: 56ddcf9a8eff16614e79ec74")
    group2 = arg_parser.add_mutually_exclusive_group(required=False)
    group2.add_argument("-http", default="False", action="store_true",
                        help="forces the tests to utilize the http API protocol")
    group2.add_argument("-https", default="False", action="store_true",
                        help="forces the tests to utilize the https API protocol")
    arg_parser.add_argument("-port", default="None",
                            help="API port number override, default from global_config.json")
    arg_parser.add_argument("-v", default=1, type=int,
                            help="Verbosity level of console output, default=0, Built Ins: " +
                                 "0: No debug, " +
                                 "2: User script output, " +
                                 "4: rest calls and status info, " +
                                 "6: other common calls (ipmi, ssh), " +
                                 "9: all the rest ")

    # parse arguments to cmd_args dict
    cmd_args = vars(arg_parser.parse_args(in_args))
    return cmd_args

def timestamp(): # return formatted current timestamp
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

# This routine executes a sleep with countdown
def countdown(sleep_time, sleep_interval=1):
    sys.stdout.write("Sleeping for " + str(sleep_time * sleep_interval)
                     + " seconds.")
    sys.stdout.flush()
    for _ in range(0, sleep_time):
        time.sleep(sleep_interval)
        sys.stdout.write(".")
        sys.stdout.flush()
    print "Waking!"
    return

def remote_shell(shell_cmd, expect_receive="", expect_send="", timeout=300,
                 address=None, user=None, password=None):
    '''
    Run ssh based shell command on a remote machine at ARGS_LIST["ora"]

    :param shell_cmd: string based command
    :param expect_receive:
    :param expect_send:
    :param timeout: in seconds
    :param address: IP or hostname of remote host
    :param user: username of remote host
    :param password: password of remote host
    :return: dict = {'stdout': str:ouput, 'exitcode': return code}
    '''
    if not address:
        address=ARGS_LIST['ora']
    if not user:
        user=ARGS_LIST['usr']
    if not password:
        password=ARGS_LIST['pwd']

    logfile_redirect = None
    if VERBOSITY >= 4:
        print "remote_shell: Host =", address
        print "remote_shell: Command =", shell_cmd

    if VERBOSITY >= 9:
        print "remote_shell: STDOUT =\n"
        logfile_redirect = sys.stdout

    # if localhost just run the command local
    if ARGS_LIST['ora'] == 'localhost':
        (command_output, exitstatus) = \
            pexpect.run("sudo bash -c \"" + shell_cmd + "\"",
                        withexitstatus=1,
                        events={"assword": password + "\n"},
                        timeout=timeout, logfile=logfile_redirect)
        return {'stdout':command_output, 'exitcode':exitstatus}

    # this clears the ssh key from ~/.ssh/known_hosts
    subprocess.call(["touch ~/.ssh/known_hosts;ssh-keygen -R "
                     + address  + " -f ~/.ssh/known_hosts >/dev/null 2>&1"], shell=True)

    shell_cmd.replace("'", "\\\'")
    if expect_receive == "" or expect_send == "":
        (command_output, exitstatus) = \
            pexpect.run("ssh -q -o StrictHostKeyChecking=no -t " + user + "@"
                        + address + " sudo bash -c \\\"" + shell_cmd + "\\\"",
                        withexitstatus=1,
                        events={"assword": password + "\n"},
                        timeout=timeout, logfile=logfile_redirect)
    else:
        (command_output, exitstatus) = \
            pexpect.run("ssh -q -o StrictHostKeyChecking=no -t " + user + "@"
                        + address + " sudo bash -c \\\"" + shell_cmd + "\\\"",
                        withexitstatus=1,
                        events={"assword": password + "\n",
                                expect_receive: expect_send + "\n"},
                        timeout=timeout, logfile=logfile_redirect)
    if VERBOSITY >= 4:
        print shell_cmd, "\nremote_shell: Exit Code =", exitstatus

    return {'stdout':command_output, 'exitcode':exitstatus}


def scp_file_to_ora(src_file_name):
    '''
    scp the given file over to the ORA and place it in onrack's
    home directory.

    :param src_file_name: name of file to copy over. May include path
    :type src_file_name: basestring
    :return: just name of file on target (no path)
    :rtype: basestring
    '''
    logfile_redirect = file('/dev/null', 'w')
    just_fname = os.path.basename(src_file_name)
    # if localhost just copy to home dir
    if ARGS_LIST['ora'] == 'localhost':
        remote_shell('cp ' + src_file_name + ' ~/' + src_file_name)
        return src_file_name

    scp_target = ARGS_LIST['usr'] + '@{0}:'.format(ARGS_LIST["ora"])
    cmd = 'scp -o StrictHostKeyChecking=no {0} {1}'.format(src_file_name, scp_target)
    if VERBOSITY >= 4:
        print "scp_file_to_ora: '{0}'".format(cmd)

    if VERBOSITY >= 9:
        logfile_redirect = sys.stdout

    (command_output, ecode) = pexpect.run(
        cmd, withexitstatus=1,
        events={'(?i)assword: ':ARGS_LIST['pwd'] + '\n'},
        logfile=logfile_redirect)
    if VERBOSITY >= 4:
        print "scp_file_to_ora: Exit Code = {0}".format(ecode)

    assert ecode == 0, \
        'failed "{0}" because {1}. Output={2}'.format(cmd, ecode, command_output)
    return just_fname

def get_auth_token():
    # This is run once to get an auth token which is set to global AUTH_TOKEN and used for rest of session
    global AUTH_TOKEN
    global REDFISH_TOKEN
    api_login = {"username": GLOBAL_CONFIG["api"]["admin_user"], "password": GLOBAL_CONFIG["api"]["admin_pass"]}
    redfish_login = {"UserName": GLOBAL_CONFIG["api"]["admin_user"], "Password": GLOBAL_CONFIG["api"]["admin_pass"]}
    try:
        restful("https://" + ARGS_LIST['ora'] + ":" + str(API_PORT) +
                       "/login", rest_action="post", rest_payload=api_login, rest_timeout=2)
    except:
        AUTH_TOKEN = "Unavailable"
        return False
    else:
        api_data = restful("https://" + ARGS_LIST['ora'] + ":" + str(API_PORT) +
                           "/login", rest_action="post", rest_payload=api_login, rest_timeout=2)
        if api_data['status'] == 200:
            AUTH_TOKEN = str(api_data['json']['token'])
            redfish_data = restful("https://" + ARGS_LIST['ora'] + ":" + str(API_PORT) +
                                   "/redfish/v1/SessionService/Sessions",
                                   rest_action="post", rest_payload=redfish_login, rest_timeout=2)
            if 'x-auth-token' in redfish_data['headers']:
                REDFISH_TOKEN = redfish_data['headers']['x-auth-token']
                return True
            else:
                print "WARNING: Redfish API token not available."
        else:
            AUTH_TOKEN = "Unavailable"
            return False

def rackhdapi(url_cmd, action='get', payload=[], timeout=None, headers={}):
    '''
    This routine will build URL for RackHD API, enable port, execute, and return data
    Example: rackhdapi('/api/current/nodes') - simple 'get' command
    Example: rackhdapi("/api/current/nodes/ID/dhcp/whitelist", action="post")

    :param url_cmd: url command for monorail api
    :param action: rest action (get/put/post/delete)
    :param payload: rest payload
    :param timeout: rest timeout
    :param headers: rest_headers

    :return: {'json':result_data.json(), 'text':result_data.text,
                'status':result_data.status_code,
                'headers':result_data.headers.get('content-type'),
                'timeout':False}
    '''

    # Automatic protocol selection: unless protocol is specified, test protocols, save settings globally
    global API_PROTOCOL
    global API_PORT

    if API_PROTOCOL == "None":
        if API_PORT == "None":
            API_PORT = str(GLOBAL_CONFIG['ports']['http'])
        if restful("http://" + ARGS_LIST['ora'] + ":" + str(API_PORT) + "/", rest_timeout=2)['status'] == 0:
            API_PROTOCOL = 'https'
            API_PORT = str(GLOBAL_CONFIG['ports']['https'])
        else:
            API_PROTOCOL = 'http'
            API_PORT = str(GLOBAL_CONFIG['ports']['http'])

    # Retrieve authentication token for the session
    if AUTH_TOKEN == "None":
        get_auth_token()

    return restful(API_PROTOCOL + "://" + ARGS_LIST['ora'] + ":" + str(API_PORT) + url_cmd,
                       rest_action=action, rest_payload=payload, rest_timeout=timeout, rest_headers=headers)

def restful(url_command, rest_action='get', rest_payload=[], rest_timeout=None, sslverify=False, rest_headers={}):
    '''
    This routine executes a rest API call to the host.

    :param url_command: the full URL for the command
    :param rest_action: what the restful do (get/post/put/delete)
    :param rest_payload: payload for rest request
    :param rest_headers: headers (JSON dict)
    :param rest_timeout: timeout for rest request
    :param sslverify: ssl Verify (True/False)
    :return:    {'json':result_data.json(), 'text':result_data.text,
                'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}
    '''

    result_data = None

    # print URL and action
    if VERBOSITY >= 4:
        print "restful: Action = ", rest_action, ", URL = ", url_command

    # prepare payload for XML output
    payload_print = []
    try:
        json.dumps(rest_payload)
    except:
        payload_print = []
    else:
        payload_print = json.dumps(rest_payload, sort_keys=True, indent=4,)
        if len(payload_print) > 4096:
            payload_print = payload_print[0:4096] + '\n...truncated...\n'
        if VERBOSITY >= 7 and rest_payload != []:
            print "restful: Payload =\n", payload_print

    rest_headers.update({"Content-Type": "application/json"})
    if VERBOSITY >= 5:
        print "restful: Request Headers =", rest_headers, "\n"

    # If AUTH_TOKEN is set, add to header
    if AUTH_TOKEN != "None" and AUTH_TOKEN != "Unavailable" and "authorization" not in rest_headers:
        rest_headers.update({"authorization": "JWT " + AUTH_TOKEN, "X-Auth-Token": REDFISH_TOKEN})
    # Perform rest request
    try:
        if rest_action == "get":
            result_data = requests.get(url_command,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       headers=rest_headers)
        if rest_action == "delete":
            result_data = requests.delete(url_command,
                                          data=json.dumps(rest_payload),
                                          timeout=rest_timeout,
                                          verify=sslverify,
                                          headers=rest_headers)
        if rest_action == "put":
            result_data = requests.put(url_command,
                                       data=json.dumps(rest_payload),
                                       headers=rest_headers,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       )
        if rest_action == "binary-put":
            rest_headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            result_data = requests.put(url_command,
                                       data=rest_payload,
                                       headers=rest_headers,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       )
        if rest_action == "text-put":
            rest_headers.update({"Content-Type": "text/plain"})
            result_data = requests.put(url_command,
                                       data=rest_payload,
                                       headers=rest_headers,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       )
        if rest_action == "post":
            result_data = requests.post(url_command,
                                        data=json.dumps(rest_payload),
                                        headers=rest_headers,
                                        timeout=rest_timeout,
                                        verify=sslverify
                                        )
        if rest_action == "binary-post":
            rest_headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            result_data = requests.post(url_command,
                                        data=rest_payload,
                                        headers=rest_headers,
                                        timeout=rest_timeout,
                                        verify=sslverify
                                        )
        if rest_action == "text-post":
            rest_headers.update({"Content-Type": "text/plain"})
            result_data = requests.post(url_command,
                                        data=rest_payload,
                                        headers=rest_headers,
                                        timeout=rest_timeout,
                                        verify=sslverify
                                        )
        if rest_action == "patch":
            result_data = requests.patch(url_command,
                                         data=json.dumps(rest_payload),
                                         headers=rest_headers,
                                         timeout=rest_timeout,
                                         verify=sslverify
                                         )
    except requests.exceptions.Timeout:
        return {'json':'', 'text':'',
                'status':0,
                'headers':'',
                'timeout':True}

    try:
        result_data.json()
    except ValueError:

        if VERBOSITY >= 9:
            print "restful: TEXT =\n"
            print result_data.text
        if VERBOSITY >= 6:
            print "restful: Response Headers =", result_data.headers, "\n"
        if VERBOSITY >= 4:
            print "restful: Status code =", result_data.status_code, "\n"
        return {'json':{}, 'text':result_data.text, 'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}
    else:

        if VERBOSITY >= 9:
            print "restful: JSON = \n"
            print json.dumps(result_data.json(), sort_keys=True, indent=4)
        if VERBOSITY >= 6:
            print "restful: Response Headers =", result_data.headers, "\n"
        if VERBOSITY >= 4:
            print "restful: Status code =", result_data.status_code, "\n"
        return {'json':result_data.json(), 'text':result_data.text,
                'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}


# Get the list of BMC IP addresses that we can find
def get_bmc_ips():
    idlist = [] # list of unique dcmi node IDs
    # If we have already done this, use that list
    if len(BMC_LIST) == 0:
        ipscan = remote_shell('arp')['stdout'].split()
        for ipaddr in ipscan:
            if ipaddr[0:3] == "172" and remote_shell('ping -c 1 -w 5 ' + ipaddr)['exitcode'] == 0:
                # iterate through all known IPMI users
                for item in GLOBAL_CONFIG['credentials']['bmc']:
                    # check BMC credentials
                    ipmicheck = remote_shell('ipmitool -I lanplus -H ' + ipaddr + ' -U ' + item['username'] \
                                               + ' -P ' + item['password'] + ' -R 1 -N 3 chassis power status')
                    if ipmicheck['exitcode'] == 0:
                        # retrieve the ID string
                        return_code = remote_shell('ipmitool -I lanplus -H ' + ipaddr + ' -U ' + item['username'] \
                                                   + ' -P ' + item['password'] + ' -R 1 -N 3 dcmi get_mc_id_string')
                        bmc_info = {"ip": ipaddr, "user": item['username'], "pw": item['password']}
                        if return_code['exitcode'] == 0 and return_code['stdout'] not in idlist:
                            # add to list if unique
                            idlist.append(return_code['stdout'])
                            BMC_LIST.append(bmc_info)
                            break
                        else:
                            # simulated nodes don't yet support dcmi, remove this else branch when supported
                            BMC_LIST.append(bmc_info)
                            break
        if VERBOSITY >= 6:
            print "get_bmc_ips: "
            print "**** BMC IP node count =", len(BMC_LIST), "****"

    return len(BMC_LIST)

# power on/off all compute nodes in the stack via the BMC
def power_control_all_nodes(state):
    if state != "on" and state != "off":
        print "power_control_all_nodes:  invalid state " + state
        return

    # Get the list of BMCs that we know about
    node_count = get_bmc_ips()

    # Send power on/off to all of them
    for bmc in BMC_LIST:
        return_code = remote_shell('ipmitool -I lanplus -H ' + bmc['ip'] \
                                   + ' -U ' + bmc['user'] + ' -P ' \
                                   + bmc['pw'] + ' -R 4 -N 3 chassis power ' + state)
        if return_code['exitcode'] != 0:
            print "Error powering " + state + " node: " + bmc['ip']

    return node_count

def mongo_reset():
    # clears the Mongo database on ORA to default, returns 0 if successful
    remote_shell('service onrack-conductor stop')
    remote_shell('/opt/onrack/bin/monorail stop')
    remote_shell("mongo pxe --eval 'db.dropDatabase\\\(\\\)'")
    remote_shell('rm -f /var/lib/dhcp/dhcpd.leases')
    remote_shell('rm -f /var/log/onrack-conductor-event.log')
    remote_shell('/opt/onrack/bin/monorail start')
    if remote_shell('service onrack-conductor start')['exitcode'] > 0:
        return 1
    return 0

def appliance_reset():

    return_code = subprocess.call("ipmitool -I lanplus -H " + ARGS_LIST["bmc"] \
                                  + " -U root -P 1234567 chassis power reset", shell=True)
    return return_code

def node_select():

    # returns a list with valid compute node IDs that match ARGS_LIST["sku"] in 'Name' or 'Model' field
    # and matches node BMC MAC address in ARGS_LIST["obmmac"] if specified
    # Otherwise returns list of all IDs that are not 'Unknown' or 'Unmanaged'
    nodelist = []
    skuid = "None"
    # check if user specified a single nodeid to run against
    # user must know the nodeid and any check for a valid nodeid is skipped
    if ARGS_LIST["nodeid"] != 'None':
        nodelist.append(ARGS_LIST["nodeid"])
        return nodelist
    else:
        # Find SKU ID
        skumap = rackhdapi('/api/2.0/skus')
        if skumap['status'] != 200:
            print '**** Unable to retrieve SKU list via API.\n'
            sys.exit(255)
        for skuentry in skumap['json']:
            if str(ARGS_LIST['sku']) in json.dumps(skuentry):
                skuid = skuentry['id']
        # Collect node IDs
        catalog = rackhdapi('/api/2.0/nodes')
        if skumap['status'] != 200:
            print '**** Unable to retrieve node list via API.\n'
            sys.exit(255)
        # Select node by SKU
        for nodeentry in catalog['json']:
            if ARGS_LIST["sku"] == 'all':
                # Select only managed compute nodes
                if nodeentry['type'] == 'compute':
                    nodelist.append(nodeentry['id'])
            else:
                if 'sku' in nodeentry and skuid in json.dumps(nodeentry['sku']):
                    nodelist.append(nodeentry['id'])
        # Select by node BMC MAC addr
        if ARGS_LIST["obmmac"] != 'all':
            idlist = nodelist
            nodelist = []
            for member in idlist:
                nodeentry = rackhdapi('/api/2.0/nodes/' + member)
                if ARGS_LIST["obmmac"] in json.dumps(nodeentry['json']):
                    nodelist = [member]
                    break
    if VERBOSITY >= 6:
        print "Node List:"
        print nodelist, '\n'
    if len(nodelist) == 0:
        print '**** Empty node list.\n'
    return nodelist

def list_skus():
    # return list of installed SKU names
    skunames = []
    api_data = rackhdapi('/api/2.0/skus')['json']
    for item in api_data:
        skunames.append(item['name'])
    return skunames

def get_node_sku(nodeid):
    # return name field of node SKU if available
    nodetype = ""
    sku = ""
    # get node info
    mondata = rackhdapi("/api/2.0/nodes/" + nodeid)
    if mondata['status'] == 200:
        # get the sku id contained in the node
        sku = mondata['json'].get("sku")
        if sku:
            skudata = rackhdapi(sku)
            if skudata['status'] == 200:
                nodetype = skudata['json'].get("name")
            else:
                if VERBOSITY >= 2:
                    errmsg = "Error: SKU API failed {}, return code {} ".format(sku, skudata['status'])
                    print errmsg
                    return "unknown"
        else:
            return "unknown"
    return nodetype

def check_active_workflows(nodeid):
    # Return True if active workflows are found on node
    workflows = rackhdapi('/api/2.0/nodes/' + nodeid + '/workflows')['json']
    for item in workflows:
        if '_status' in item:
            if item['_status'] in ['running', 'pending']:
                return True
        if 'status' in item:
            if item['status'] in ['running', 'pending']:
                return True
        else:
            return False
    return False

def cancel_active_workflows(nodeid):
    # cancel all active workflows on node
    exitstatus = True
    apistatus = rackhdapi('/api/2.0/nodes/' + nodeid + '/workflows/action',
                          action='put', payload={"command": "cancel"})['status']
    if apistatus != 202:
        exitstatus = False
    return exitstatus

def apply_obm_settings(retry=30):
    # New routine to install OBM credentials via workflows in parallel
    count = 0
    for creds in GLOBAL_CONFIG['credentials']['bmc']:
        # greate graph for setting OBM credentials
        payload = \
        {
            "friendlyName": "IPMI" + str(count),
            "injectableName": 'Graph.Obm.Ipmi.CreateSettings' + str(count),
            "options": {
                "obm-ipmi-task":{
                    "user": creds["username"],
                    "password": creds["password"]
                }
            },
            "tasks": [
                {
                    "label": "obm-ipmi-task",
                    "taskName": "Task.Obm.Ipmi.CreateSettings"
                }
        ]
        }
        api_data = rackhdapi("/api/2.0/workflows/graphs", action="put", payload=payload)
        if api_data['status'] != 201:
            print "**** OBM workflow failed to load!"
            return False
        count += 1
    # Setup additional OBM settings for nodes that currently use RMM port (still same bmc username/password used)
    count = 0
    for creds in GLOBAL_CONFIG['credentials']['bmc']:
        # greate graph for setting OBM credentials for RMM
        payload = \
        {
            "friendlyName": "RMM.IPMI" + str(count),
            "injectableName": 'Graph.Obm.Ipmi.CreateSettings.RMM' + str(count),
            "options": {
                "obm-ipmi-task":{
                    "ipmichannel": "3",
                    "user": creds["username"],
                    "password": creds["password"]
                }
            },
            "tasks": [
                {
                    "label": "obm-ipmi-task",
                    "taskName": "Task.Obm.Ipmi.CreateSettings"
                }
        ]
        }
        api_data = rackhdapi("/api/2.0/workflows/graphs", action="put", payload=payload)
        if api_data['status'] != 201:
            print "**** OBM workflow failed to load!"
            return False
        count += 1

    # run each OBM credential workflow on each node in parallel until success
    nodestatus = {} # dictionary with node IDs and status of each node
    for dummy in range(0, retry):
        nodelist = node_select()
        for node in nodelist:
            if node not in nodestatus:
                nodestatus[node] = {"status": "pending", "instanceId": "", "sku": get_node_sku(node), "retry": 0}
        for num in range(0, count):
            for node in nodelist:
                # try workflow
                if nodestatus[node]['status'] == "pending":
                    skuid = rackhdapi('/api/2.0/nodes/' + node)['json'].get("sku")
                    if skuid:
                        if nodestatus[node]['sku'] == "unknown":
                            nodestatus[node].update({"sku": get_node_sku(node)})
                        skudata = rackhdapi(skuid)['text']
                        if "rmm.data.MAC" in skudata:
                            workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings.RMM' + str(num)}
                        else:
                            workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings' + str(num)}
                        result = rackhdapi("/api/2.0/nodes/"  + node + "/workflows", action="post", payload=workflow)
                        if result['status'] == 201:
                            nodestatus[node].update({"status": "running", "instanceId": result['json']["instanceId"]})
            for node in nodelist:
                # check OBM workflow status
                if nodestatus[node]['status'] == "running":
                    nodestatus[node]['retry'] += 1
                    state_data = rackhdapi("/api/2.0/workflows/" + nodestatus[node]['instanceId'])
                    if state_data['status'] == 200:
                        if "_status" in state_data['json']:
                            state = state_data['json']['_status']
                        else:
                            state = state_data['json']['status']
                        if state == "succeeded":
                            nodestatus[node]['status'] = "succeeded"
                        if state in ["failed", "cancelled", "timeout"]:
                            nodestatus[node]['status'] = "pending"
                            # if the workflow left an invalid OBM, delete it
                            result = rackhdapi("/api/2.0/nodes/" + node)
                            if result['status'] == 200:
                                if result['json']['obms']:
                                    for ref in result['json']['obms']:
                                        obmref = ref.get('ref')
                                        if obmref:
                                            rackhdapi(obmref, action="delete")

        if VERBOSITY >= 4:
            print "**** Node(s) OBM status:\n", json.dumps(nodestatus, sort_keys=True, indent=4,)
        if "pending" not in str(nodestatus) and "running" not in str(nodestatus):
            # All OBM settings successful
            return True
        time.sleep(30)
    # Failures occurred
    print "**** Node(s) OBM settings failed."
    return False

def apply_obm_settings_seq():
    # legacy routine to install OBM credentials via workflows sequentially one-at-a-time
    count = 0
    for creds in GLOBAL_CONFIG['credentials']['bmc']:
        # greate graph for setting OBM credentials
        payload = \
        {
            "friendlyName": "IPMI" + str(count),
            "injectableName": 'Graph.Obm.Ipmi.CreateSettings' + str(count),
            "options": {
                "obm-ipmi-task":{
                    "user": creds["username"],
                    "password": creds["password"]
                }
            },
            "tasks": [
                {
                    "label": "obm-ipmi-task",
                    "taskName": "Task.Obm.Ipmi.CreateSettings"
                }
        ]
        }
        api_data = rackhdapi("/api/2.0/workflows/graphs", action="put", payload=payload)
        if api_data['status'] != 201:
            print "**** OBM workflow failed to load!"
            return False
        count += 1
    # Setup additional OBM settings for nodes that currently use RMM port (still same bmc username/password used)
    count = 0
    for creds in GLOBAL_CONFIG['credentials']['bmc']:
        # greate graph for setting OBM credentials for RMM
        payload = \
        {
            "friendlyName": "RMM.IPMI" + str(count),
            "injectableName": 'Graph.Obm.Ipmi.CreateSettings.RMM' + str(count),
            "options": {
                "obm-ipmi-task":{
                    "ipmichannel": "3",
                    "user": creds["username"],
                    "password": creds["password"]
                }
            },
            "tasks": [
                {
                    "label": "obm-ipmi-task",
                    "taskName": "Task.Obm.Ipmi.CreateSettings"
                }
        ]
        }
        api_data = rackhdapi("/api/2.0/workflows/graphs", action="put", payload=payload)
        if api_data['status'] != 201:
            print "**** OBM workflow failed to load!"
            return False
        count += 1

    # run each OBM workflow against each node until success
    nodelist = node_select()
    failedlist = []
    for node in nodelist:
        for num in range(0, count):
            nodestatus = ""
            wfstatus = ""
            skuid = rackhdapi('/api/2.0/nodes/' + node)['json'].get("sku")
            # Check is sku is empty
            sku = skuid.rstrip("/api/2.0/skus/")
            if sku:
                skudata = rackhdapi(skuid)['text']
                if "rmm.data.MAC" in skudata:
                    workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings.RMM' + str(num)}
                else:
                    workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings' + str(num)}
            else:
                print "*** SKU not set for node ", node
                nodestatus = "failed"
                break

            # wait for existing workflow to complete
            for dummy in range(0, 60):
                print "*** Using workflow: ", workflow
                result = rackhdapi("/api/2.0/nodes/"  + node + "/workflows", action="post", payload=workflow)
                if result['status'] != 201:
                    time.sleep(5)
                elif dummy == 60:
                    print "*** Workflow failed to start"
                    wfstatus = "failed"
                else:
                    break

            if wfstatus != "failed":
                # wait for OBM workflow to complete
                counter = 0
                for counter in range(0, 60):
                    time.sleep(10)
                    state_data = rackhdapi("/api/2.0/workflows/" + result['json']["instanceId"])
                    if state_data['status'] == 200:
                        if "_status" in state_data['json']:
                            nodestatus = state_data['json']['_status']
                        else:
                            nodestatus = state_data['json']['status']
                        if nodestatus != "running" and nodestatus != "pending":
                            break
                if nodestatus == "succeeded":
                    print "*** Succeeded on workflow ", workflow
                    break
                if counter == 60:
                    #print "Timed out status", nodestatus
                    nodestatus = "failed"
                    print "*** Node failed OBM settings - timeout:", node
                    print "*** Failed on workflow ", workflow

        # check final loop status for node workflow
        if wfstatus == "failed" or nodestatus == "failed":
            failedlist.append(node)

    # cleanup failed nodes OBM settings on nodes, need to remove failed settings
    for node in failedlist:
        result = rackhdapi("/api/2.0/nodes/"  + node)
        if result['status'] == 200:
            if result['json']['obms']:
                obms = result['json']['obms'][0]
                obmref = obms.get('ref')
                if obmref:
                    result = rackhdapi(obmref, action="delete")
                    if result['status'] != 204:
                        print "*** Warning: failed to delete invalid OBM setting ", obmref

    if len(failedlist) > 0:
        print "**** Nodes failed OBM settings:", failedlist
        return False
    return True

def run_nose(nosepath=None):

    if not nosepath:
        nosepath = cfg()['cmd-args-list']['test']

    # this routine runs nosetests from wrapper using path spec 'nosepath'
    def _noserunner(pathspecs, noseopts):
        xmlfile = str(time.time()) + ".xml" # XML report file name
        env = {
            'VERBOSITY':  str(ARGS_LIST['v']),
            'ORA':  str(ARGS_LIST['ora']),
            'STACK':  str(ARGS_LIST['stack']),
            'SKU':  str(ARGS_LIST['sku']) ,
            'NODEID':  str(ARGS_LIST['nodeid']),
            'OBMMAC':  str(ARGS_LIST['obmmac']),
            'VERSION':  str(ARGS_LIST['version']),
            'TEMPLATE':  str(ARGS_LIST['template']),
            'XUNIT':  str(ARGS_LIST['xunit']),
            'NUMVMS':  str(ARGS_LIST['numvms']),
            'GROUP':  str(ARGS_LIST['group']),
            'CONFIG':  str(ARGS_LIST['config']),
            'HTTP':  str(ARGS_LIST['http']),
            'HTTPS':  str(ARGS_LIST['https']),
            'PORT':  str(ARGS_LIST['port']),
            'FIT_CONFIG': mkcfg().get_path(),
            'HOME':  os.environ['HOME'],
            'PATH':  os.environ['PATH']
        }
        argv = ['nosetests']
        argv.extend(noseopts)
        argv.append('--xunit-file')
        argv.append(xmlfile)
        argv.extend(pathspecs)
        return subprocess.call(argv, env=env)

    exitcode = 0
    # set nose options
    noseopts = ['--exe', '--with-nosedep', '--with-stream-monitor']
    if ARGS_LIST['group'] != 'all' and ARGS_LIST['group'] != '':
        noseopts.append('-a')
        noseopts.append(str(ARGS_LIST['group']))
    if ARGS_LIST['list'] == True or ARGS_LIST['list'] == "True":
        noseopts.append('--collect-only')
        ARGS_LIST['v'] = 0
        print "\nTest Listing for:", ARGS_LIST['test']
        print "----------------------------------------------------------------------"
    if ARGS_LIST['xunit'] == True or ARGS_LIST['xunit'] == "True":
        noseopts.append('--with-xunit')
    else:
        noseopts.append('-s')
        noseopts.append('-v')

    # if nosepath is a directory, recurse through subdirs else run single test file
    if os.path.isdir(nosepath):
        # Skip the CIT test directories that match these expressions
        regex = '(tests$)|(tests/api$)|(tests/api/.*)'
        pathspecs = []
        for root, _, _ in os.walk(nosepath):
            if not re.search(regex, root):
                pathspecs.append(root)
        exitcode += _noserunner(pathspecs, noseopts)
    else:
        exitcode += _noserunner([nosepath], noseopts)
    return exitcode

def run_from_module(file_name):
    # Use this method in 'name == "__main__"' style test invocations
    # within individual test files
    run_nose(file_name)

# determine who imported us.
importer=inspect.getframeinfo(inspect.getouterframes(inspect.currentframe())[1][0])[0]
if 'run_tests.py' in importer:
    # we are being imported through run_tests.py (the fit wrapper)
    # process sys.args as received by run_tests.py
    compose_config(True)

    # Bridge between old and new.  Remove when conversion complete
    compose_global_config()

else:
    # we are being imported directly through a unittest module
    # args will be nose-base args
    compose_config(False)

    # Bridge between old and new.  Remove when conversion complete
    compose_global_config()
