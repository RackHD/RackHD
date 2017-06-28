'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

RackHD common test utlitiies

Authors:
Ericka Hohenstein
yuchi zhang
George Paulos

Purpose/intent
This utility library contain helper functions for parsing response data from the RackHD APIs.
'''

import fit_path  # NOQA: unused import
import fit_common
import unicodedata

##########################################
#  Node List Utils
##########################################


def rackhd_get_node_list():
    """
    this function returns the list of node ids reported by
    the Monrail API /api/2.0/nodes
    :return:
        computer node list in that stack when success.
        otherwise on failure
    """
    monurl = "/api/2.0/nodes"
    mondata = fit_common.rackhdapi(url_cmd=monurl)
    nodes = mondata['json']

    nodelist = []
    if len(nodes) == 0:
        if fit_common.VERBOSITY >= 2:
            print "No Nodes found on RackHD server "
    else:
        inode = 0
        while inode < len(nodes):
            nodelist.append(nodes[inode]["id"])
            inode += 1
    return nodelist


def get_rackhd_nodetype(nodeid):
    nodetype = "unknown"
    sku = ""
    # get node info
    mondata = fit_common.rackhdapi("/api/2.0/nodes/" + nodeid)
    if mondata['status'] == 200:
        # get the sku id contained in the node
        sku = mondata['json'].get("sku")
        if sku:
            skudata = fit_common.rackhdapi(sku)
            if skudata['status'] == 200:
                nodetype = skudata['json'].get("name")
            else:
                if fit_common.VERBOSITY >= 2:
                    errmsg = "Error: SKU API failed {}, return code {} ".format(sku, skudata['status'])
                    print errmsg
        else:
            if fit_common.VERBOSITY >= 2:
                errmsg = "Error: nodeid {} did not return a valid sku in get_rackhd_nodetype {}".format(nodeid, sku)
                print errmsg
    return nodetype


def get_node_list_by_type(node_type):
    """
    Get node list according to type (like PDU, compute)
    :param type:
    :return: node id list for given type
    """
    node_info = fit_common.rackhdapi(url_cmd="/api/2.0/nodes?type=" + node_type)
    node_list = []
    if node_info["status"] in [200, 201, 202, 204]:
        for node in node_info["json"]:
            node_list.append(node["id"])
    return node_list


def delete_nodes_by_type(node_type):
    """
    Delete all nodes for a given node_type
    :param node_type:
    :return:
    """
    node_list = []
    node_list = get_node_list_by_type(node_type)
    if node_list == []:
        return 0
    for node_id in node_list:
        fit_common.cancel_active_workflow(node_id)
        fit_common.rackhdapi(url_cmd="/api/2.0/nodes/" + node_id, action="delete")
    node_list = get_node_list_by_type(node_type)
    if node_list == []:
        return 0
    else:
        return -1

##########################################
#  Compute Node Utils
##########################################


def get_obm_port_ip(node_id):
    """
    Return the IP address of the management port of a compute node

    :param node_id: the id of the node.
    :return: String based ip address on success.            1 on URL error,
            2 on parsing error,
            otherwise on other errors
    """

    rest_res = {'json': "", 'text': "", 'status': "", 'headers': ""}

    str_uri = '/api/2.0/nodes/' + node_id
    rest_res = fit_common.rackhdapi(url_cmd=str_uri)
    if rest_res['status'] != 200:
        if fit_common.VERBOSITY >= 2:
            print "Unable to get the " \
                "MAC address of target Node.\nURL: \t" +\
                '/api/2.0/nodes/' + node_id
        return 1

    if 'obms' in rest_res['json'] and 'ref' in rest_res['json']['obms']['0']:
        mac_address = fit_common.rackhdapi(rest_res['json']['obms']['0']['ref'])['json']['config']['host']
        if not mac_address:
            if fit_common.VERBOSITY >= 2:
                print "Unable to find out the MAC address " \
                      "associated with the node from http request.\n"
                print rest_res['json']
            return 2
    else:
        if fit_common.VERBOSITY >= 2:
            print "obmSettings is not found by the request:" \
                  "\n\t" + "URL:\t" + str_uri
            print rest_res['json']
        return 2

    str_uri = '/api/2.0/lookups?q=' + mac_address
    rest_res = fit_common.rackhdapi(url_cmd=str_uri)
    if rest_res['status'] != 200:
        if fit_common.VERBOSITY >= 2:
            print "Unable to get the IP address from the MAC address:\n\tURL:\t" +\
                  '/api/2.0/lookups?q=' + mac_address
        return 1

    try:
        ret_ip_address = rest_res['json'][0]['ipAddress']
    except (IndexError, KeyError) as e:
        if fit_common.VERBOSITY >= 2:
            print e
            print "Unable to parse out obm ip address from MAC address query.\n"
            print rest_res['json']
        return 2

    return ret_ip_address


def get_compute_bmc_ip(node_id):
    """
    Return the BMC IP address by given the ID of computing node.
    :param node_id: The node ID used for identify the computing node.
    :return: String of BMC ip address on success,
            1 on network error,
            2 on parsing error,
            otherwise on other errors
    """

    monorail_url = "/api/2.0/nodes/" + node_id + "/catalogs/bmc"
    rest_res = {'json': "", 'text': "", 'status': "", 'headers': ""}

    rest_res = fit_common.rackhdapi(url_cmd=monorail_url)
    if rest_res['status'] != 200:
        if fit_common.VERBOSITY >= 2:
            print "Error in getting bmc web request"
        return 1

    if rest_res['json']['data']['IP Address'] != "":
        ret_ip = rest_res['json']['data']['IP Address']
        return ret_ip
    else:
        return 2


def get_compute_rmm_ip(node_id):
    """
    Return the RMM IP address by given the ID of computing node.
    :param node_id: The node ID used for identify the computing node.
    :return: String of RMM ip address on success,
            1 on network error,
            2 on parsing error,
            otherwise on other errors
    """
    monorail_url = "/api/2.0/nodes/" + node_id + "/catalogs/rmm"
    rest_res = {'json': "", 'text': "", 'status': "", 'headers': ""}

    rest_res = fit_common.rackhdapi(url_cmd=monorail_url)
    if rest_res['status'] != 200:
        if fit_common.VERBOSITY >= 2:
            print "Error in getting bmc web request"
        return 1
    if rest_res['json']['data']['IP Address'] != "":
        ret_ip = rest_res['json']['data']['IP Address']
        return ret_ip
    else:
        return 2


def get_compute_node_username(node_id):
    """
    Get the username credential from node id
    :param node_id: The id given by OnRack
    :return:
        dict_credential = {"user": user_name, "password": password}
        1 on network error
        2 on parsing error
        3 on unable to obtain password from username
        4 Get compute node credentials failure
        Otherwise
    """
    monorail_url = "/api/2.0/nodes/" + node_id
    rest_res = {'json': "", 'text': "", 'status': "", 'headers': ""}
    rest_res = fit_common.rackhdapi(url_cmd=monorail_url)

    if rest_res['status'] != 200:
        if fit_common.VERBOSITY >= 2:
            print "Error in getting response with url\n\t" + monorail_url
        return 1

    node_info = rest_res['json']

    try:
        obm_list = node_info['obms']
        obm_url = obm_list[0]['ref']
        obm_data = fit_common.rackhdapi(obm_url, action="get")
        if obm_data['status'] != 200:
            if fit_common.VERBOSITY >= 2:
                print "Error in getting response with obm data\n\t" + obm_url
            return 1

        username = obm_data['json']['config'].get('user')
        if username:
            user = unicodedata.normalize('NFKD', username).encode('ascii', 'ignore')
        else:
            if fit_common.VERBOSITY >= 2:
                print "Unable to obtain the user name from node id given"
            return 2

        if user:
            password = guess_the_password(user)
        else:
            if fit_common.VERBOSITY >= 2:
                print "Unable to obtain the user name from test host and node id"
            return 2

        if password is None:
            if fit_common.VERBOSITY >= 2:
                print "Unable to obtain the password from test host and node id"
            return 3

        ret_dict_cred = {"user": user, "password": password}
        return ret_dict_cred

    except:
        if fit_common.VERBOSITY >= 2:
            print "ERROR: Get compute node credentials failed"
        return 4


def get_relations_for_node(node_id):
    """
    Get encl id for a given node id
    Or get node id list for a give enclosure id
    :param node_id: node id
    :return: enclosure id list for a given node or node id list for a given enclosure
    """

    mon_url = "/api/2.0/nodes/" + node_id
    mon_data = fit_common.rackhdapi(url_cmd=mon_url)
    if mon_data['status'] not in [200, 201, 202, 204]:
        return None
    node_relations = mon_data["json"].get("relations", "")
    for relation in node_relations:
        if "enclose" in relation["relationType"]:
            return relation["targets"]
    return None

##########################################
#  IPMI Node Utils
##########################################


def guess_the_password(str_username):
    """
    Guess the password according to the username
    :param str_username: string based username
    :return: string based password on success, 1 on unable to guess
    """
    dict_cheat_sheet = {}
    for entry in fit_common.fitcreds()['bmc']:
        dict_cheat_sheet[entry['username']] = entry['password']
    if (str_username in dict_cheat_sheet) \
            and (dict_cheat_sheet[str_username] != ""):
        return dict_cheat_sheet[str_username]
    else:
        return None


def run_ipmi_command(node_ip, str_command, dict_credential):
    """
    Run ipmi command and check its return code
    :param node_ip: ip address of the server to run the ipmicommand against
    :param str_command:  the ipmitools string command
    :param dict_credential: the credential to run ipmitool command
    :return: result of remote_shell
    """
    remote_ssh_res = {'stdout': "", 'exitcode': 0}
    str_ipmi_cmd = "ipmitool -I lanplus -H " +\
                   node_ip + " -U " +\
                   dict_credential['user'] +\
                   " -P " + dict_credential['password'] +\
                   " " + str_command

    remote_ssh_res = fit_common.remote_shell(shell_cmd=str_ipmi_cmd)
    if remote_ssh_res['exitcode'] != 0:
        if fit_common.VERBOSITY >= 2:
            print "Error in execute # ipmitool on " + node_ip

    return remote_ssh_res


def run_ipmi_command_to_node(node_id, str_ipmi_cmd):
    """
    Run a ipmi command to the node_id
    :param node_id: the node in that OnRack
    :param str_ipmi_cmd: the option that is attached to ipmitool
    :return: running result on success.
             Different return codes otherwise.
    """
    str_ip = get_compute_bmc_ip(node_id)
    if (str_ip == 2 or str_ip == 1) or str_ip == '0.0.0.0':
        if fit_common.VERBOSITY >= 2:
            print "Unable to find the bmc ip at given node id"
        return 1

    dict_cred = get_compute_node_username(node_id)
    if dict_cred == 1 or dict_cred == 2 or dict_cred == 3:
        if fit_common.VERBOSITY >= 2:
            print "No username or password found at given node id"
        return 1
    return run_ipmi_command(str_ip, str_ipmi_cmd, dict_cred)

##########################################
#  Poller Utils
##########################################


def get_poller_data_by_id(poller_id):
    """
    To get the poller data by poller id
    """
    poller_data = []
    monurl = "/api/2.0/pollers/" + str(poller_id) + "/data"
    mondata = fit_common.rackhdapi(url_cmd=monurl)
    if mondata['status'] in [200, 201, 202, 204]:
        poller_data = mondata['json']
    else:
        if fit_common.VERBOSITY >= 2:
            print "Status {}, Failed to get data for poller id: {}".format(mondata['status'], str(poller_id))
    return poller_data


def get_supported_pollers(node_id):
    """
    To get a poller dictionary, the keys are poller names, and the values are poller_id, poller_interval, etc
    """
    poller_dict = {}

    monurl = "/api/2.0/nodes/" + str(node_id) + "/pollers"
    mondata = fit_common.rackhdapi(url_cmd=monurl)

    if mondata['status'] not in [200, 201, 202, 204]:
        if fit_common.VERBOSITY >= 2:
            print "Status: {},  Failed to get pollers for node: {}".format(mondata['status'], node_id)
    else:
        pollers = mondata['json']
        poller_dict = dict()
        for poller in pollers:
            if "metric" in poller["config"]:
                poller_name = poller["config"]["metric"]
            else:
                poller_name = poller["config"]["command"]
                poller_interval = poller["pollInterval"]
                poller_id = poller["id"]
                poller_dict[poller_name] = {'poller_id': poller_id, 'poller_interval': poller_interval}

    return poller_dict


def get_ora_poller_id_list():
    """
    Get all poller ids for an onrack system
    :return: poller id list
    """
    mon_url = "/api/2.0/pollers"
    mon_data = fit_common.rackhdapi(url_cmd=mon_url)
    if mon_data['status'] not in [200, 201, 202, 204]:
        return -1
    ora_poller_list = []
    for poller in mon_data["json"]:
        ora_poller_list.append(poller["id"])
    return ora_poller_list

##########################################
#  RackHD Catalog Utils
##########################################


def get_catalogue_from_source(node_id, source):
    """
    To get the catalogue data by the source name

    Check the basic fields where there should be values, and return the data for the source
    """
    monurl = "/api/2.0/nodes/" + str(node_id) + "/catalogs/" + str(source)
    mondata = fit_common.rackhdapi(url_cmd=monurl)

    if mondata['status'] in [200, 201, 202, 204]:
        mon_json = mondata['json']
        if mon_json.get('node', None) != str(node_id) or mon_json.get('source', None) \
                != str(source) or not mon_json.get('createdAt', None) or not mon_json.get('updatedAt', None):
            return -1
        else:
            return mon_json.get('data')
    else:
        return -1


def get_catalogue_sources(node_id):
    """
    To get the list of sources names from catalogue
    returns empty list on error
    """
    monurl = "/api/2.0/nodes/" + str(node_id) + "/catalogs"
    mondata = fit_common.rackhdapi(url_cmd=monurl)

    sources_list = []
    if mondata['status'] not in [200, 201, 202, 204]:
        return sources_list
    try:
        mon_json = mondata['json']
    except:
        return sources_list

    for catalog in mon_json:
        source_name = catalog['source']
        sources_list.append(source_name)

    return sources_list


def get_node_source_id_list(node_id):
    """
    Get all catalog source ids for a given node
    :param node_id:
    :return: source name and source id as a dictionary
             empty dict if not found
    """
    ora_source_list = dict()
    mon_url = "/api/2.0/nodes/" + node_id + "/catalogs"
    mon_data = fit_common.rackhdapi(url_cmd=mon_url)
    if mon_data['status'] in [200, 201, 202, 204]:
        for source in mon_data["json"]:
            ora_source_list[source["source"]] = source["id"]
    return ora_source_list


def get_ora_source_id_list():
    """
    Get all catalog source ids for a onrack system
    :return: source id list
             empty list if not found
    """
    ora_source_list = []
    mon_url = "/api/2.0/catalogs"
    mon_data = fit_common.rackhdapi(url_cmd=mon_url)
    if mon_data['status'] in [200, 201, 202, 204]:
        for source in mon_data["json"]:
            ora_source_list.append(source["id"])
    return ora_source_list


def get_catalog_by_source_id(source_id):
    """
    Get catalog data by source id
    :param source_id: catalog source id
    :return: catalog data with specified source id
    """
    mon_url = "/api/2.0/catalogs/" + str(source_id)
    mon_data = fit_common.rackhdapi(url_cmd=mon_url)
    if mon_data['status'] in [200, 201, 202, 204]:
        return mon_data['json']
    return None
