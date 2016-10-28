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

# Globals

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
    "list": os.getenv("LIST", False), # list tests
    "group": os.getenv("GROUP", "all"), # test group
    "http": os.getenv("HTTP", "False"), # force http api protocol
    "https": os.getenv("HTTPS", "False"), # force https api protocol
    "port": os.getenv("PORT", "None") # port number override
}

# Get top level path via git
TEST_PATH = subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/"
CONFIG_PATH = TEST_PATH + ARGS_LIST["config"] + "/"
if ARGS_LIST["config"] != 'config':
    print "**** Using config file path:", ARGS_LIST["config"]
VERBOSITY = int(os.getenv("VERBOSITY", "1"))
GLOBAL_CONFIG = []
STACK_CONFIG = []
API_PORT = "None"
API_PROTOCOL = "None"
AUTH_TOKEN = "None"
REDFISH_TOKEN = "None"

# List of BMC IP addresses
BMC_LIST = []


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

def remote_shell(shell_cmd, expect_receive="", expect_send="", timeout=300, address=ARGS_LIST['ora'], user=ARGS_LIST['usr'], password=ARGS_LIST['pwd']):
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

    scp_target = 'onrack@{0}:'.format(ARGS_LIST["ora"])
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
                               "/redfish/v1/SessionService/Sessions", rest_action="post", rest_payload=redfish_login, rest_timeout=2)
            if 'x-auth-token' in redfish_data['headers']:
                REDFISH_TOKEN =  redfish_data['headers']['x-auth-token']
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
            rest_headers.update({"Content-Type": "application/octet-stream"})
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
            rest_headers.update({"Content-Type": "application/octet-stream"})
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
        else:
            if VERBOSITY >= 2:
                errmsg = "Error: nodeid {} did not return a valid sku in get_rackhd_nodetype{}".format(nodeid,sku)
                print errmsg
    return nodetype

def check_active_workflows(nodeid):
    # Return True if active workflows are found on node
    workflows = rackhdapi('/api/2.0/nodes/' + nodeid + '/workflows')['json']
    for item in workflows:
        if 'running' in item['_status'] or 'pending' in item['_status']:
            return True
    return False

def cancel_active_workflows(nodeid):
    # cancel all active workflows on node
    exitstatus = True
    apistatus = rackhdapi('/api/2.0/nodes/' + nodeid + '/workflows/action',
                          action='put', payload={"command": "cancel"})['status']
    if apistatus != 202:
       exitstatus = False
    return exitstatus

def apply_obm_settings_new():
    # Experimental routine to install OBM credentials via workflows
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
    nodelist = node_select()
    nodestatus = {} # dictionary with node IDs and status of each node
    for node in nodelist:
        nodestatus[node]= {"status": "pending", "instanceId": "", "sku": get_node_sku(node), "retry": 0}
    for dummy in range(0, 60):
        for num in range(0, count):
            for node in nodelist:
                skuid = rackhdapi('/api/2.0/nodes/' + node)['json'].get("sku")
                skudata = rackhdapi(skuid)['text']
                if "rmm.data.MAC" in skudata:
                    workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings.RMM' + str(num)}
                else:
                    workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings' + str(num)}
                # try workflow
                if nodestatus[node]['status'] == "pending":
                    for dummy in range(0, 60):
                        # retry if other workflows active
                        result = rackhdapi("/api/2.0/nodes/"  + node + "/workflows", action="post", payload=workflow)
                        if result['status'] == 201:
                            nodestatus[node].update({"status": "running", "instanceId": result['json']["instanceId"], "retry": 0})
                            break
                        else:
                           time.sleep(5)
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
        if VERBOSITY > 4:
            print "**** Node(s) OBM status:\n", json.dumps(nodestatus, sort_keys=True, indent=4,)
        if "pending" not in str(nodestatus) and "running" not in str(nodestatus):
            # All OBM settings successful
            return True
        time.sleep(10)
    # Failures occurred
    print "**** Node(s) OBM settings failed."
    return False

def apply_obm_settings():
    # legacy routine to install OBM credentials via workflows
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
            skuid = rackhdapi('/api/2.0/nodes/' + node)['json'].get("sku")
            skudata = rackhdapi(skuid)['text']
            if "rmm.data.MAC" in skudata:
                workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings.RMM' + str(num)}
            else:
                workflow = {"name": 'Graph.Obm.Ipmi.CreateSettings' + str(num)}
            # wait for existing workflow to complete
            for dummy in range(0, 60):
                result = rackhdapi("/api/2.0/nodes/"  + node + "/workflows", action="post", payload=workflow)
                if result['status'] != 201:
                    time.sleep(5)
                else:
                    break
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
                break
            if counter == 60:
                failedlist.append(node)
    if len(failedlist) > 0:
        print "**** Nodes failed OBM settings:", failedlist
        return False
    return True

def run_nose(nosepath):
    # this routine runs nosetests from wrapper using path spec 'nosepath'
    def _noserunner(pathspec):
        xmlfile = str(time.time()) + ".xml" # XML report file name
        return subprocess.call(
                         [
                             'export VERBOSITY=' + str(ARGS_LIST['v']) + ';' +
                             'export ORA=' + str(ARGS_LIST['ora']) + ';' +
                             'export STACK=' + str(ARGS_LIST['stack']) + ';' +
                             'export SKU="' + str(ARGS_LIST['sku']) + '";' +
                             'export NODEID=' + str(ARGS_LIST['nodeid']) + ';' +
                             'export OBMMAC=' + str(ARGS_LIST['obmmac']) + ';' +
                             'export VERSION=' + str(ARGS_LIST['version']) + ';' +
                             'export TEMPLATE=' + str(ARGS_LIST['template']) + ';' +
                             'export XUNIT=' + str(ARGS_LIST['xunit']) + ';' +
                             'export GROUP=' + str(ARGS_LIST['group']) + ';' +
                             'export CONFIG=' + str(ARGS_LIST['config']) + ';' +
                             'export HTTP=' + str(ARGS_LIST['http']) + ';' +
                             'export HTTPS=' + str(ARGS_LIST['https']) + ';' +
                             'export PORT=' + str(ARGS_LIST['port']) + ';' +
                             'nosetests ' + noseopts + ' --xunit-file ' + xmlfile + ' ' + pathspec
                         ], shell=True)
    exitcode = 0
    # set nose options
    noseopts = ' --exe '
    if ARGS_LIST['group'] != 'all' and ARGS_LIST['group'] != '':
        noseopts += ' -a ' + str(ARGS_LIST['group']) + ' '
    if ARGS_LIST['list'] == True or ARGS_LIST['list'] == "True":
        noseopts += ' -v --collect-only '
        ARGS_LIST['v'] = 0
        print "\nTest Listing for:", ARGS_LIST['test']
        print "----------------------------------------------------------------------"
    if ARGS_LIST['xunit'] == True or ARGS_LIST['xunit'] == "True":
        noseopts += ' --with-xunit '
    else:
        noseopts += ' -s '
    # if nosepath is a directory, recurse through subdirs else run single test file
    if os.path.isdir(nosepath):
        cmdline = ""
        for subdir, dirs, files in os.walk(nosepath):
            cmdline += " " + subdir
        exitcode += _noserunner(cmdline)
    else:
        exitcode += _noserunner(nosepath)
    return exitcode

