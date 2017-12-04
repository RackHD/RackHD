'''
Copyright 2017, Dell, Inc.

Author(s):

common methods for ucs tests

'''

import fit_path  # NOQA: unused import
from common import fit_common
import time
import flogging
from config.settings import get_ucs_cred
from ucsmsdk import ucshandle
from ucsmsdk.utils.ucsbackup import import_ucs_backup
import os

logs = flogging.get_loggers()

INITIAL_NODES = {}
INITIAL_OBMS = {}
MAX_WAIT = 240
UCSM_IP = fit_common.fitcfg().get('ucsm_ip')
UCSM_USER = fit_common.fitcfg().get('ucsm_user')
UCSM_PASS = fit_common.fitcfg().get('ucsm_pass')
EXPECTED_UCS_PHYSICAL_NODES = 22
if fit_common.fitcfg().get('physical_nodes_count') is not None:
    EXPECTED_UCS_PHYSICAL_NODES = int(fit_common.fitcfg().get('physical_nodes_count'))
UCS_SERVICE_URI = fit_common.fitcfg().get('ucs_service_uri')


def get_nodes_utility():
    """
    Takes inventory of the nodes available before discovering the UCS nodes.
    We will restore the nodes collection to this snapshot
    :return: return False on failure, or True otherwise
    """
    api_data = fit_common.rackhdapi('/api/2.0/nodes')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/nodes returned status {}, expected 200".format(api_data['status']))
        return False

    for node in api_data['json']:
        INITIAL_NODES[node['id']] = node['type']
    logs.info_1("Found {0} Nodes before testing UCS cases. {1}"
                .format(len(INITIAL_NODES), INITIAL_NODES))
    return True


def get_obms_utility():
    """
    Takes inventory of the obms available before discovering the UCS obms.
    We will restore the obms collection to this snapshot.
    :return: return False on failure, or True otherwise
    """
    api_data = fit_common.rackhdapi('/api/2.0/obms')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/obms returned status {}, expected 200".format(api_data['status']))
        return False

    for obm in api_data['json']:
        INITIAL_OBMS[obm['id']] = obm['service']
    logs.info_1("Found {0} obms before testing UCS cases: {1}".format(len(INITIAL_OBMS), INITIAL_OBMS))
    return True


def restore_node_utility():
    """
    Deletes all the added ucs nodes by the test.
    :return: return False on failure, or True otherwise
    """
    logs.info_1("Restoring Nodes")
    api_data = fit_common.rackhdapi('/api/2.0/nodes')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/nodes returned status {}, expected 200".format(api_data['status']))
        return False

    for node in api_data['json']:
        if node['id'] not in INITIAL_NODES:
            api_data = fit_common.rackhdapi('/api/2.0/nodes/' + node['id'], action="delete")
            logs.info_1("Deleting Node: {0}. Status was: {1}".format(node['id'], api_data['status']))

    api_data = fit_common.rackhdapi('/api/2.0/nodes')

    if api_data['status'] != 200:
        logs.error("get /api/2.0/nodes returned status {}, expected 200".format(api_data['status']))
        return False

    temp = {}
    for node in api_data['json']:
        temp[node['id']] = node['name']

    if len(temp) != len(INITIAL_NODES):
        logs.error("Found {0}  nodes remaining after restoring the nodes, should be {1}, Remaining nodes: {2}"
                   .format(len(temp), len(INITIAL_NODES), temp))
        return False

    return True


def restore_obms_utility():
    """
     Deletes all the added ucs obms by this test.
    :return:
    """
    logs.info_1("Restoring OBMs")

    api_data = fit_common.rackhdapi('/api/2.0/obms')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/obms returned status {}, expected 200".format(api_data['status']))
        return False

    for obm in api_data['json']:
        if obm['id'] not in INITIAL_OBMS:
            api_data = fit_common.rackhdapi('/api/2.0/obms/' + obm['id'], action="delete")
            logs.info_1("Deleting OBM: {0}. Status was: {1}".format(obm['id'], str(api_data['status'])))

    api_data = fit_common.rackhdapi('/api/2.0/obms')
    if api_data['status'] != 200:
        logs.error("get /api/2.0/obms returned status {}, expected 200".format(api_data['status']))
        return False

    temp = {}
    for obm in api_data['json']:
        temp[obm['id']] = obm['service']
    if len(temp) != len(INITIAL_OBMS):
        logs.error("Found {0} ucs obms remaining after restoring the obms, should be {1}. Remaining OBMs: {2}"
                   .format(len(temp), len(INITIAL_OBMS), temp))
        return False

    return True


def load_ucs_manager_config():
    """
    loads the test configuration into the UCS Manger
    """
    logs.info_1('Loading UCSPE emulator from {0}'.format(fit_common.fitcfg()['ucsm_config_file']))

    try:
        handle = ucshandle.UcsHandle(UCSM_IP, UCSM_USER, UCSM_PASS)
        if not handle.login():
            logs.error('Failed to log into UCS Manger!')
            return False
    except Exception as e:
        logs.info_1("error trying to log into UCS Manger!")
        logs.info_1(str(e))
        return False

    # now try to update the UCSPE config, if this fails we can still continue
    try:
        path, file = os.path.split(fit_common.fitcfg()['ucsm_config_file'])
        import_ucs_backup(handle, file_dir=path, file_name=file)
    except Exception as e:
        logs.info_1("error trying to configure UCSPE, continuing to test")
        logs.info_1(str(e))
        # log the error but do not return a failure, we can still run some tests with the default config

    if not handle.logout():
        logs.error('Failed to log out of UCS Manger during exit!')
        return False

    return True


def get_physical_server_count():
    """
    Get a count of the number of Service Proviles defined by the UCS Manager
    """
    url = UCS_SERVICE_URI + "/rackmount"

    headers = {"ucs-user": UCSM_USER,
               "ucs-password": UCSM_PASS,
               "ucs-host": UCSM_IP}

    api_data = fit_common.restful(url, rest_headers=headers)
    if api_data['status'] != 200:
        logs.error('Incorrect HTTP return code, expected 200, got: {0}'.format(api_data['status']))
        return 0

    count = len(api_data["json"])
    url = UCS_SERVICE_URI + "/chassis"
    api_data = fit_common.restful(url, rest_headers=headers)
    if api_data['status'] != 200:
        logs.error('Incorrect HTTP return code, expected 200, got: {0}'.format(api_data['status']))
        return 0

    count += len(api_data["json"])
    for element in api_data["json"]:
        count += len(element["members"])
    return count


def get_service_profile_count():
    """
    Get a count of the number of Service Proviles defined by the UCS Manager
    """
    url = UCS_SERVICE_URI + "/serviceProfile"
    headers = {"ucs-user": UCSM_USER,
               "ucs-password": UCSM_PASS,
               "ucs-host": UCSM_IP}

    api_data = fit_common.restful(url, rest_headers=headers)
    if api_data['status'] != 200:
        logs.error('Incorrect HTTP return code, expected 200, got: {0}'.format(api_data['status']))
        return 0

    return len(api_data["json"]["ServiceProfile"]["members"])


def wait_utility(id, counter, name, max_wait=MAX_WAIT):
    """
    Wait for the specified graph to finish
    :param id:  Graph ID
    :param counter: Safeguard for the number of times we can check the status of the graph
    :param name: Description of graph we are waiting for
    :return: returns status of the taskgraph, or "timeout" if count is exceeded
    """
    api_data = fit_common.rackhdapi('/api/2.0/workflows/' + str(id))
    status = api_data["json"]["status"]
    logs.info_1("Waiting up to {0} seconds for {1} Workflow, ID: {2}"
                .format(max_wait, name, id))
    while (status == 'running' and counter < max_wait):
        time.sleep(1)
        counter += 1
        api_data = fit_common.rackhdapi('/api/2.0/workflows/' + str(id))
        status = api_data["json"]["status"]

    if counter >= max_wait:
        logs.info_1("wait_utility() timed out after {0} attemps. status: {1}, ID: {2}, name: {3}"
                    .format(counter, id, name))
        return 'timeout'
    else:
        logs.info_1("wait_utility() copleted with status: {0} for run: {1}. ID: {2}, name: {3}"
                    .format(status, counter, id, name))
        return status


def is_ucs_valid():
    if UCSM_IP is None:
        logs.error("Expected value for UCSM_IP other then None and found {0}".format(UCSM_IP))
        return False
    if UCS_SERVICE_URI is None:
        logs.error("Expected value for UCS_SERVICE_URI other then None and found {0}".format(UCS_SERVICE_URI))
        return False

    if "ucsm_config_file" in fit_common.fitcfg():
        # configure the UCSPE emulator
        if not load_ucs_manager_config():
            # error configureing UCSPE emulaotr, skip all tests
            logs.error("Error Configuring UCSPE emulator, skipping all UCS tests")
            return False

        # wait up to 2 min for config to be valid
        timeout = 120
        ucsCount = get_physical_server_count()
        while (ucsCount) != EXPECTED_UCS_PHYSICAL_NODES:
            if timeout <= 0:
                logs.error("Only found {0} of {1} nodes, skipping all UCS tests"
                           .format(ucsCount, EXPECTED_UCS_PHYSICAL_NODES))
                return False
            logs.info_1("Only found {0} of {1} ucs nodes, retrying in 30 seconds"
                        .format(ucsCount, EXPECTED_UCS_PHYSICAL_NODES))
            timeout -= 5
            time.sleep(5)
            ucsCount = get_physical_server_count()
    return True
