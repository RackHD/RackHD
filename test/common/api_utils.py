"""
Copyright 2016, EMC, Inc.
"""

from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from config.api2_0_config import config
from json import loads
from common.fit_common import fitargs
import flogging
logs = flogging.get_loggers()

HTTP_NOT_FOUND = 404


def __fitargs_get(key):
    arg = fitargs()[key]
    if not isinstance(arg, str) or arg == 'all':
        arg = None
    return arg


def api_node_select_from_config(node_type='compute', validate_obm=False, allow_unknown_nodes=False):
    """
    This routine produces a list of node Ids that satisfy the requested parameters.
    Nodes may be filtered by Node Id,  SKU name, OBM MAC address which are defined
    in the system environment.  The node type and OBM setting may be specified.
    :param  node_type: Node type (i.e. compute) (default= 'compute')
    :param  validate_obm: should the node have OBM settings (default=False)
    return: A list with node IDs that match node type, SKU, and possible valid OBM settings.
    :param  allow_unknown_nodes: should nodes have a SKU assigned (default=False)
    """
    return api_node_select(config.api_client,
                           node_id=__fitargs_get("nodeid"),
                           sku_name=__fitargs_get("sku"),
                           obm_mac=__fitargs_get("obmmac"),
                           node_type=node_type,
                           validate_obm=validate_obm,
                           allow_unknown_nodes=allow_unknown_nodes
                           )


def api_node_select(client,
                    node_id=None,
                    sku_name=None,
                    obm_mac=None,
                    node_type='compute',
                    validate_obm=False,
                    allow_unknown_nodes=False
                    ):
    """
    This routine produces a list of node Ids that satisfy the requested parameters.
    Nodes may be filtered by Node Id,     SKU name, OBM MAC address, or node type.
    The OBM setting may also be validated (validate_obm).
    Note: Validation of obm setting is not provides if node id is specified.
    :param  client: reference to config.api2_0_config
    :param  node_id: ID of node object (default=None)
    :param  sku_name: Name of sku (default='None')
    :param  obm_mac: OBM mac address (default='None')
    :param  node_type: Node type (i.e. compute) (default= 'compute')
    :param  validate_obm: should the node have OBM settings (default=False)
    :param  allow_unknown_nodes: should nodes have a SKU assigned (default=False)
    return: A list with node IDs that match node type, SKU, and possible valid OBM settings.
    """
    node_id_list = list()
    sku_id = None
    sku_list = list()
    # if user specified single node id, don't bother getting sku information
    if not node_id:
        #
        # Get a list of the current SKU objects
        #
        try:
            Api().skus_get()
            sku_list_rsp = client.last_response
            sku_list = loads(sku_list_rsp.data)
        except (TypeError, ValueError) as e:
            assert e.message
        except ApiException as e:
            # Can't get a sku so leave sku_id as None
            logs.irl.warning('Unable to retrieve SKU list via API. status (%s)', e.status)

        # Search the list of sku objects for the possible requested sku name. This is skipped if
        # the requested sku name is None.
        if sku_list and sku_name:
            for sku_entry in sku_list:
                if sku_name == sku_entry['name']:
                    sku_id = sku_entry['id']
                    break

    #
    # Collect a list of node objects that match node type and possible sku type
    #
    try:
        Api().nodes_get_all()
    except (TypeError, ValueError) as e:
        assert e.message
    except ApiException as e:
        # There is no chance of getting any nodes so return an empty list
        logs.irl.error('Unable to retrieve node list via API. status (%s)', e.status)
        return []

    node_list_rsp = client.last_response
    node_list = loads(node_list_rsp.data)

    # Select node by node type and SKU
    for node_entry in node_list:
        if node_id and node_id == node_entry['id']:
            # check if user specified a single node_id to run against
            # user must know the node_id and any check for a valid node_id is skipped
            node_id_list = [node_id]
            break
        elif not obm_mac:
            # We are searching for all nodes with the requested sku
            if not sku_name:
                # Select only managed compute nodes
                if not node_type or node_entry['type'] == node_type:
                    if ('sku' in node_entry and node_entry['sku']) or allow_unknown_nodes:
                        if not validate_obm or validate_obm_settings(client, node_entry['id']):
                            node_id_list.append(node_entry['id'])
            else:
                if sku_id and node_entry.get('sku') and sku_id in node_entry['sku']:
                    if not validate_obm or validate_obm_settings(client, node_entry['id']):
                        node_id_list.append(node_entry['id'])
        else:
            # we are looking for a particular node with the requested OBM MAC
            try:
                Api().nodes_get_obms_by_node_id(identifier=node_entry['id'])
            except (TypeError, ValueError) as e:
                assert e.message
            except ApiException as e:
                # There is no chance of getting the requested obm object using this node id, just
                # try another node.
                if e.status != HTTP_NOT_FOUND:
                    logs.irl.warning('Unable to retrieve obm list via API for node: %s status: (%s).',
                                     node_entry['id'],
                                     e.status)
                continue

            obm_list_rsp = client.last_response
            obm_list = loads(obm_list_rsp.data)

            # does this node use the requested OBM MAC
            for obm_entry in obm_list:
                host = get_by_string(obm_entry, 'config.host')
                if host:
                    if ':' in host and host.lower() == obm_mac.lower():
                        node_id_list = [node_entry['id']]
                        break

            # determine if the MAC was found, if so exit node loop
            if node_id_list:
                break

    # we now have a node ID list
    if not node_id_list:
        logs.irl.debug('Empty node ID list.')
    return node_id_list


def api_validate_node_pollers(client, node_id_list, all_pollers=False):
    """
    This function validates that the presented list of node contains active pollers. By default
    only the fist poller of the pollers associated with a node is validated. Setting the
    'all_pollers' flag to True allows all poller associated with a node to be validated.
    :param  client: reference to config.api2_0_config
    :param  node_id_list - list of node ids
    :param  all_pollers - Test all poller assocaited with a node (default: False)
    return: True  - all nodes have active poller
            False - all nodes do not have active pollers
    """
    pollers_list = list()

    if not isinstance(node_id_list, (tuple, list, set)):
        logs.irl.error('Provided node_list is not a [list]')

        # return no good pollers
        return False

    for node_id in node_id_list:
        try:
            Api().nodes_get_pollers_by_id(node_id)
        except (TypeError, ValueError) as e:
            assert e.message
        except ApiException as e:
            if e.status != HTTP_NOT_FOUND:
                logs.irl.error('Unable to retrieve node: %s pollers via API. status (%s)', node_id, e.status)
            # unable to get poller for this node, so return a False
            return False

        rsp = client.last_response
        node_poller_list = loads(rsp.data)

        # if the poller return None or an empty list, return a False
        if not node_poller_list:
            logs.irl.debug('Node %s has no pollers.', node_id)
            # no poller on this node, so return a False
            return False

        for poller in node_poller_list:
            pollers_list.append(poller)
            if not all_pollers:
                # all_pollers is False so only validate the first poller
                break

    for poller in pollers_list:
        try:
            Api().pollers_data_get(poller['id'])
        except (TypeError, ValueError) as e:
            assert e.message
        except ApiException as e:
            if e.status != HTTP_NOT_FOUND:
                logs.irl.error('pollers_data_get() failed (%s) node: %s poller: %s command: %s',
                               e.status,
                               poller['node'],
                               poller['id'],
                               poller['config']['command'])
            return False

        poller_rsp = client.last_response
        poller_data = loads(poller_rsp.data)

        logs.irl.debug('node: %s poller: %s command: %s',
                       poller['node'],
                       poller['id'],
                       poller['config']['command'])

        if poller_rsp.status == 200:
            # This will process a status of 200
            if not poller_data:
                logs.irl.warning('No poller data for node: %s poller: %s command: %s',
                                 poller['node'],
                                 poller['id'],
                                 poller['config']['command'])
                return False
        else:
            # This assumes a status of 204
            if poller_data:
                logs.irl.warning('Unexpected poller data for node %s poller %s command %s',
                                 poller['node'],
                                 poller['id'],
                                 poller['config']['command'])
                return False

    return True


def validate_obm_settings(client, identifier):
    """
    The OBM objects are obtained for the requested node. They are then searched to
    determine if at least one has OBM settings.
    :param  client: reference to config.api2_0_config
    :param  identifier: ID of node object
    return: True  - node have OBM setting
            False - node does not have OBM settings
    """
    try:
        Api().nodes_get_obms_by_node_id(identifier=identifier)
    except (TypeError, ValueError) as e:
        assert e.message
    except ApiException as e:
        # There is no chance of getting the requested obm object using this node id, just
        # return False to indicate no OBM settings
        if e.status != HTTP_NOT_FOUND:
            logs.irl.warning('Unable to retrieve obm list via API for node:: %s status: (%s).',
                             identifier,
                             e.status)
        return False

    obm_list_rsp = client.last_response
    obm_list = loads(obm_list_rsp.data)

    # determine if this node possible credentials
    # TODO: additional tests may be required
    for obm_entry in obm_list:
        if get_by_string(obm_entry, 'config.user'):
            return True
        if get_by_string(obm_entry, 'config.properties.community'):
            return True
    return False


def get_by_string(source_dict, search_string, default_if_not_found=None):
    """
    Search a dictionary using keys provided by the search string.
    The search string is made up of keywords separated by a '.'
    Example: 'fee.fie.foe.fum'
    :param source_dict: the dictionary to search
    :param search_string: search string with keyword separated by '.'
    :param default_if_not_found: Return value if search is un-successful
    :return value, dictionary or default_if_not_found
    """
    if not source_dict or not search_string:
        return default_if_not_found

    dict_obj = source_dict

    for search_key in search_string.split("."):
        try:
            dict_obj = next(val for key, val in dict_obj.iteritems() if key == search_key)
        except StopIteration:
            return default_if_not_found
    return dict_obj
