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
from mkcfg import mkcfg

sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test")

VERBOSITY = 1
TEST_PATH = None
CONFIG_PATH = None
API_PORT = "None"
API_PROTOCOL = "None"
AUTH_TOKEN = "None"
REDFISH_TOKEN = "None"
BMC_LIST = []

def fitcfg():
    """
    returns the configuration dictionary
    :return: dictionary
    """
    return mkcfg().get()

def fitrackhd():
    """
    returns the ['rackhd-config'] dictionary
    :return: dictionary or None
    """
    return fitcfg().get('rackhd-config', None)

def fitargs():
    """
    returns the ['cmd-args-list'] dictionary
    :return: dictionary or None
    """
    return fitcfg().get('cmd-args-list', None)

def fitcreds():
    """
    returns the ['credentials'] dictionary
    :return: dictionary or None
    """
    return fitcfg().get('credentials', None)

def fitinstall():
    """
    returns the ['install-config']['install'] dictionary
    :return: dictionary or None
    """
    if 'install-config' not in fitcfg():
        return None
    return fitcfg()['install-config'].get('install', None)

def fitports():
    """
    returns the ['install-config']['ports'] dictionary
    :return: dictionary or None
    """
    if 'install-config' not in fitcfg():
        return None
    return fitcfg()['install-config'].get('ports', None)

def fitcit():
    """
    returns the ['cit-config'] dictionary
    :return: dictionary or None
    """
    return fitcfg().get('cit-config', None)

def fitglobals():
    """
    returns the ['install-config']['global'] dictionary
    :return: dictionary or None
    """
    return fitcfg().get('globals', None)

def fitproxy():
    """
    returns the ['install-config']['proxy'] dictionary
    :return: dictionary or None
    """
    if 'install-config' not in fitcfg():
        return None
    return fitcfg()['install-config'].get('proxy', None)

def fitskupack():
    if 'install-config' not in fitcfg():
        return None
    return fitcfg()['install-config'].get('skupack', None)

def compose_config(use_sysargs=False):
    """
    creates a configuration based on
    :param use_sysargs: set to true if sys.argv is to be processed.
    :return: None
    """
    # create configuration object
    cfg_obj = mkcfg()
    if cfg_obj.config_is_loaded():
        # a previously generated configuration has been loaded
        # restore previously setup globals
        update_globals()
    else:
        # create new configuration
        #   * add cmd-args-list section
        #   * add the default config json file composition.
        #   * add stack overlay
        #   * save off environment
        #   * generate a few globals
        #   * save (generate) the configuration to a file
        args_list = {}
        if use_sysargs:
            # Args from command line, pass -config option to create
            args_list['cmd-args-list'] = mkargs()
            config = args_list['cmd-args-list']['config']
            cfg_obj.create(config)
        else:
            # Args from default set
            no_args = {}
            args_list['cmd-args-list'] = mkargs(no_args)
            cfg_obj.create()

        # add the 'cmd-args-list' section
        cfg_obj.add_from_dict(args_list)

        if fitargs()['config'] != 'config':
            print "*** Using config file path:", fitcfg()['cmd-args-list']['config']

        if cfg_obj.get_path() is None:

            default_composition = ['rackhd_default.json',
                                   'credentials_default.json',
                                   'install_default.json',
                                   'cit_default.json']

            # config file composition
            cfg_obj.add_from_file_list(default_composition)

            # stack overlay configuration
            apply_stack_config()

            # add significant environment variables
            args = fitargs()
            cfg_obj.add_from_dict({
                'env': {
                    'HOME':  os.environ['HOME'],
                    'PATH':  os.environ['PATH']
                }
            })

            add_globals()

            # generate the configuration file
            cfg_obj.generate()
            print "*** Using config file: {0}".format(cfg_obj.get_path())

def apply_stack_config():
    """
    does the necessary stack configuration changes
    :return: None
    """
    stack = fitargs()['stack']
    if stack is not None:
        mkcfg().add_from_file('stack_config.json', stack)
        if 'ora' in fitcfg():
            fitargs()['ora'] = fitcfg()['ora']
        else:
            fitargs()['ora'] = 'localhost'
        if 'bmc' in fitcfg():
            fitargs()['bmc'] = fitcfg()['bmc']
        if 'hyper' in fitcfg():
            fitargs()['hyper'] = fitcfg()['hyper']

def add_globals():
    """
    create a handlful of global shortcuts
    :return:
    """
    global TEST_PATH
    global CONFIG_PATH
    global API_PORT
    global API_PROTOCOL
    global VERBOSITY

    # set api port and protocol from command line
    if fitargs()['port'] != "None":
        API_PORT = fitargs()['port']

    if fitargs()['http'] == "True":
        API_PROTOCOL = "http"
        if API_PORT == "None":
            API_PORT = fitports()['http']

    if fitargs()['https'] == "True":
        API_PROTOCOL = "https"
        if API_PORT == "None":
            API_PORT = fitports()['https']

    if fitargs()["ora"] == "localhost":
        if API_PROTOCOL == "None":
            API_PROTOCOL = 'http'
        if API_PORT == "None":
            API_PORT = '8080'

    # add globals section to base configuration
    TEST_PATH = subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/"
    CONFIG_PATH = TEST_PATH + fitargs()['config'] + "/"
    mkcfg().add_from_dict({
        'globals': {
            'API_PORT': API_PORT,
            'API_PROTOCOL': API_PROTOCOL,
            'TEST_PATH': TEST_PATH,
            'CONFIG_PATH': CONFIG_PATH,
            'VERBOSITY' : fitargs()['v']
        }
    })

    # set OVA template from command line
    if fitargs()["template"] == "None":
        fitargs()["template"] = fitcfg()['install-config']['template']


def update_globals():
    global API_PORT
    global API_PROTOCOL
    global TEST_PATH
    global CONFIG_PATH
    global VERBOSITY

    API_PORT = fitglobals()['API_PORT']
    API_PROTOCOL = fitglobals()['API_PROTOCOL']
    TEST_PATH = fitglobals()['TEST_PATH']
    CONFIG_PATH = fitglobals()['CONFIG_PATH']
    VERBOSITY = fitglobals()['VERBOSITY']

def mkargs(in_args=None):
    """
    processes the command line options as passed in by in_args.
    :param in_args: input arguments
    :return: dictionary of processed arguments
    """
    if in_args is None:
        in_args = sys.argv[1:]

    # command line argument parser returns cmd_args dict
    arg_parser = argparse.ArgumentParser(
        description="Command Help", add_help=False)
    arg_parser.add_argument('-h', '--help', action='store_true', default=False,
                            help='show this help message and exit')
    arg_parser.add_argument("-test", default="tests/",
                            help="test to execute, default: tests/")
    arg_parser.add_argument("-config", default="config",
                            help="config file location, default: config")
    arg_parser.add_argument("-group", default="all",
                            help="test group to execute: 'smoke', 'regression', 'extended', default: 'all'")
    arg_parser.add_argument("-stack", default="vagrant",
                            help="stack label (test bed), overrides -ora")
    arg_parser.add_argument("-ora", default="localhost",
                            help="OnRack/RackHD appliance IP address or hostname, default: localhost")
    arg_parser.add_argument("-version", default="onrack-devel",
                            help="OnRack package install version, example:onrack-release-0.3.0, default: onrack-devel")
    arg_parser.add_argument("-template", default="None",
                            help="path or URL link to OVA template or OnRack OVA")
    arg_parser.add_argument("-xunit", default="False", action="store_true",
                            help="generates xUnit XML report files")
    arg_parser.add_argument("-numvms", default=1, type=int,
                            help="number of virtual machines for deployment on specified stack")
    arg_parser.add_argument("-list", default="False", action="store_true",
                            help="generates test list only")
    arg_parser.add_argument("-sku", default="all",
                            help="node SKU name, example: Quanta-T41, default=all")
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
                            help="API port number override, default from install_config.json")
    arg_parser.add_argument("-v", default=4, type=int,
                            help="Verbosity level of console and log output (see -nose-help for more options), Built Ins: " +
                                 "0: Minimal logging, "+
                                 "1: Display ERROR and CRITICAL to console and to files, " +
                                 "3: Display INFO to console and to files, " +
                                 "4: (default) Display INFO to console, and DEBUG to files, " +
                                 "5: Display infra.run and test.run DEBUG to both, " +
                                 "6: Add display of test.data (rest calls and status) DEBUG to both, " +
                                 "7: Add display of infra.data (ipmi, ssh) DEBUG to both, " +
                                 "9: Display infra.* and test.* at DEBUG_9 (max output) ")
    arg_parser.add_argument("-nose-help", default=False, action="store_true", dest="nose_help",
                            help="display help from underlying nosetests command, including additional log options")
    # we want to grab the arguments we want, and pass the rest
    # into the nosetest invocation.
    parse_results, other_args = arg_parser.parse_known_args(in_args)

    # if 'help' was set, handle it as best we can. We use argparse to
    # display usage and arguments, and then give nose a shot at printing
    # things out (if they set that option)
    if parse_results.help:
        arg_parser.print_help()
        if parse_results.nose_help:
            print
            print "NOTE: below is the --help output from nosetests."
            print
            rcode = _run_nose_help()
        else:
            rcode = 0
        sys.exit(rcode)

    # And if they only did --nose-help
    if parse_results.nose_help:
        rcode = _run_nose_help()
        sys.exit(rcode)

    # Now handle mapping -v to infra-logging. Check stream-monitor/flogging/README.md
    # for how loggers and handlers fit together.
    if parse_results.v >= 9:
        # Turn them all up to 11.
        vargs = ['--sm-set-combo-level', 'console*', 'DEBUG_9']
    elif parse_results.v >= 7:
        # ends up turning everything up to DEBUG_5 (levels 5 + 6 + infra.data)
        vargs = ['--sm-set-combo-level', 'console*', 'DEBUG_5']
    elif parse_results.v >= 6:
        # infra.run and test.* to DEBUG (level 5 + test.data)
        vargs = ['--sm-set-combo-level', 'console*:(test.data|*.run)', 'DEBUG_5']
    elif parse_results.v >= 5:
        # infra and test.run to DEBUG
        vargs = ['--sm-set-combo-level', 'console*:*.run', 'DEBUG_5']
    elif parse_results.v >= 4:
        # default
        vargs = []
    elif parse_results.v >= 3:
        # dial BACK output to files to INFO_5
        vargs = ['--sm-set-logger-level', '*', 'INFO_5']
    elif parse_results.v >= 1:
        # dial BACK output to everything to just ERROR, CRITICAL to console and logs
        vargs = ['--sm-set-combo-level', '*', 'ERROR_5']
    else:
        # 0 and 1 currently try to squish ALL logging output.
        vargs = ['--sm-set-combo-level', '*', 'CRITICAL_0']

    other_args.extend(vargs)

    # Put all the args we did not use and put them
    # into the parse_results so they can be found
    # by run_nose()
    parse_results.unhandled_arguments = other_args

    # parse arguments to cmd_args dict
    cmd_args = vars(parse_results)
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
    Run ssh based shell command on a remote machine at fitargs()["ora"]

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
        address = fitargs()['ora']
    if not user:
        user = fitcreds()['ora'][0]['username']
    if not password:
        password = fitcreds()['ora'][0]['password']

    logfile_redirect = None
    if VERBOSITY >= 4:
        print "remote_shell: Host =", address
        print "remote_shell: Command =", shell_cmd

    if VERBOSITY >= 9:
        print "remote_shell: STDOUT =\n"
        logfile_redirect = sys.stdout

    # if localhost just run the command local
    if fitargs()['ora'] == 'localhost':
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
    if fitargs()['ora'] == 'localhost':
        remote_shell('cp ' + src_file_name + ' ~/' + src_file_name)
        return src_file_name

    scp_target = fitcreds()['ora'][0]['username'] + '@{0}:'.format(fitargs()["ora"])
    cmd = 'scp -o StrictHostKeyChecking=no {0} {1}'.format(src_file_name, scp_target)
    if VERBOSITY >= 4:
        print "scp_file_to_ora: '{0}'".format(cmd)

    if VERBOSITY >= 9:
        logfile_redirect = sys.stdout

    (command_output, ecode) = pexpect.run(
        cmd, withexitstatus=1,
        events={'(?i)assword: ':fitcreds()['ora'][0]['password'] + '\n'},
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
    api_login = {"username": fitcreds()["api"][0]["admin_user"], "password": fitcreds()["api"][0]["admin_pass"]}
    redfish_login = {"UserName": fitcreds()["api"][0]["admin_user"], "Password": fitcreds()["api"][0]["admin_pass"]}
    try:
        restful("https://" + fitargs()['ora'] + ":" + str(API_PORT) +
                       "/login", rest_action="post", rest_payload=api_login, rest_timeout=2)
    except:
        AUTH_TOKEN = "Unavailable"
        return False
    else:
        api_data = restful("https://" + fitargs()['ora'] + ":" + str(API_PORT) +
                           "/login", rest_action="post", rest_payload=api_login, rest_timeout=2)
        if api_data['status'] == 200:
            AUTH_TOKEN = str(api_data['json']['token'])
            redfish_data = restful("https://" + fitargs()['ora'] + ":" + str(API_PORT) +
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
            API_PORT = str(fitports()['http'])
        if restful("http://" + fitargs()['ora'] + ":" + str(API_PORT) + "/", rest_timeout=2)['status'] == 0:
            API_PROTOCOL = 'https'
            API_PORT = str(fitports()['https'])
        else:
            API_PROTOCOL = 'http'
            API_PORT = str(fitports()['http'])

    # Retrieve authentication token for the session
    if AUTH_TOKEN == "None":
        get_auth_token()

    return restful(API_PROTOCOL + "://" + fitargs()['ora'] + ":" + str(API_PORT) + url_cmd,
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
        return {'json':{}, 'text':'',
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
                for item in fitcreds()['bmc']:
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

    return_code = subprocess.call("ipmitool -I lanplus -H " + fitargs()["bmc"] \
                                  + " -U root -P 1234567 chassis power reset", shell=True)
    return return_code

def node_select():

    # returns a list with valid compute node IDs that match fitargs()["sku"] in 'Name' or 'Model' field
    # and matches node BMC MAC address in fitargs()["obmmac"] if specified
    # Otherwise returns list of all IDs that are not 'Unknown' or 'Unmanaged'
    nodelist = []
    skuid = "None"
    # check if user specified a single nodeid to run against
    # user must know the nodeid and any check for a valid nodeid is skipped
    if fitargs()["nodeid"] != 'None':
        nodelist.append(fitargs()["nodeid"])
        return nodelist
    else:
        # Find SKU ID
        skumap = rackhdapi('/api/2.0/skus')
        if skumap['status'] != 200:
            print '**** Unable to retrieve SKU list via API.\n'
            sys.exit(255)
        for skuentry in skumap['json']:
            if str(fitargs()['sku']) in json.dumps(skuentry):
                skuid = skuentry['id']
        # Collect node IDs
        catalog = rackhdapi('/api/2.0/nodes')
        if skumap['status'] != 200:
            print '**** Unable to retrieve node list via API.\n'
            sys.exit(255)
        # Select node by SKU
        for nodeentry in catalog['json']:
            if fitargs()["sku"] == 'all':
                # Select only managed compute nodes
                if nodeentry['type'] == 'compute':
                    nodelist.append(nodeentry['id'])
            else:
                if 'sku' in nodeentry and skuid in json.dumps(nodeentry['sku']):
                    nodelist.append(nodeentry['id'])
        # Select by node BMC MAC addr
        if fitargs()["obmmac"] != 'all':
            idlist = nodelist
            nodelist = []
            for member in idlist:
                nodeentry = rackhdapi('/api/2.0/nodes/' + member)
                if fitargs()["obmmac"] in json.dumps(nodeentry['json']):
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
    for creds in fitcreds()['bmc']:
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
    for creds in fitcreds()['bmc']:
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
    for creds in fitcreds()['bmc']:
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
    for creds in fitcreds()['bmc']:
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
        nosepath = fitcfg()['cmd-args-list']['test']

    # this routine runs nosetests from wrapper using path spec 'nosepath'
    def _noserunner(pathspecs, noseopts):
        xmlfile = str(time.time()) + ".xml" # XML report file name
        env = {
            'FIT_CONFIG': mkcfg().get_path(),
            'HOME':  os.environ['HOME'],
            'PATH':  os.environ['PATH']
        }
        argv = ['nosetests']
        argv.extend(noseopts)
        argv.append('--xunit-file')
        argv.append(xmlfile)
        argv.extend(pathspecs)
        argv.extend(fitcfg()['cmd-args-list']['unhandled_arguments'])
        return subprocess.call(argv, env=env)

    exitcode = 0
    # set nose options
    noseopts = ['--exe', '--with-nosedep', '--with-stream-monitor']
    if fitargs()['group'] != 'all' and fitargs()['group'] != '':
        noseopts.append('-a')
        noseopts.append(str(fitargs()['group']))
    if fitargs()['list'] == True or fitargs()['list'] == "True":
        noseopts.append('--collect-only')
        fitargs()['v'] = 0
        print "\nTest Listing for:", fitargs()['test']
        print "----------------------------------------------------------------------"
    if fitargs()['xunit'] == True or fitargs()['xunit'] == "True":
        noseopts.append('--with-xunit')
    else:
        noseopts.append('-s')
        noseopts.append('-v')

    # if nosepath is a directory, recurse through subdirs else run single test file
    if os.path.isdir(nosepath):
        # Skip the CIT test directories that match these expressions
        regex = '(tests/*$)|(tests/api-cit/*)|(tests/api$)|(tests/api/.*)'
        pathspecs = []
        for root, _, _ in os.walk(nosepath):
            if not re.search(regex, root):
                pathspecs.append(root)
        exitcode += _noserunner(pathspecs, noseopts)
    else:
        exitcode += _noserunner([nosepath], noseopts)
    return exitcode

def _run_nose_help():
    # This is used ONLY to fire off 'nosetests --help' for use from mkargs() when
    # it is handling --help itself.
    argv = ['nosetests', '--help']
    return subprocess.call(argv)

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

else:
    # we are being imported directly through a unittest module
    # args will be nose-base args
    compose_config(False)

