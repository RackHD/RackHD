from on_http_api2_0 import ApiApi as Api
from config.api2_0_config import config
from json import loads
import sys
import os



def api_node_select_argsList(node_type='compute', validate_obm=False):
    """
    This routine produces a list of node Ids that satisfy the requested parameters. 
    Nodes may be filtered by Node Id,  SKU name, OBM MAC address which are defined
    in the system environment.  The node type and OBM setting may be specified.
    :param  node_type: Node type (i.e. compute) (default= 'compute')
    :param  validate_obm: should the node have OBM settings (default=False)
    return: A list with node IDs that match node type, SKU, and possible valid OBM settings.
    """
    return api_node_select(config.api_client,
                           node_id=os.getenv("node_id", "None"),
                           sku_name=os.getenv("SKU", "all"),
                           obm_mac=os.getenv("obm_mac", "all"),
                           node_type=node_type,
                           validate_obm=validate_obm,
                           verbosity=os.getenv("VERBOSITY", "0")
                           )



def api_node_select(client,
                    node_id=None,
                    sku_name='all',
                    obm_mac='all',
                    node_type='compute',
                    validate_obm=False,
                    verbosity=None
                    ):
    """
    This routine produces a list of node Ids that satisfy the requested parameters. 
    Nodes may be filtered by Node Id,     SKU name, OBM MAC address, or node type. 
    The OBM setting may also be validated (validate_obm).
    Note: Validation of obm setting is not provides if node id is specified.
    :param  client: reference to config.api2_0_config
    :param  node_id: ID of node object (default=None)
    :param  sku_name: Name of sku (default='all')
    :param  obm_mac: OBM mac address (default='all')
    :param  node_type: Node type (i.e. compute) (default= 'compute')
    :param  validate_obm: should the node have OBM settings (default=False)
    return: A list with node IDs that match node type, SKU, and possible valid OBM settings.
    """

    node_id_list = []
    sku_id = "None"

    # set verbosity level
    if not verbosity:
        verbosity = os.getenv("VERBOSITY", "0")

    # if user specified single node id, don't bother getting sku information
    if not node_id:
        #
        # Get a list of the current SKU objects
        #
        Api().skus_get()
        sku_list_rsp = client.last_response
        sku_list = loads(sku_list_rsp.data)

        # Determine if the list was obtained without error
        if sku_list_rsp.status != 200:
            # Can't get a sku so leave sku_id as None
            print '**** Unable to retrieve SKU list via API. status ({})\n'.format(sku_list_rsp.status)

        # Search the list of sku objects for the possible requested sku name. This is skipped if
        # the requested sku name is 'all', which will then use the default value of sku_id ('None')
        elif sku_name != 'all':
            for sku_entry in sku_list:
                if sku_name == sku_entry['name']:
                    sku_id = sku_entry['id']
                    break

    #
    # Collect a list of node objects that match node type and possible sku type
    #
    Api().nodes_get_all()
    node_list_rsp = client.last_response
    node_list = loads(node_list_rsp.data)

    # Determine if the list was obtained without error
    if node_list_rsp.status != 200:
        # There is no chance of getting any nodes so return an empty list
        print '**** Unable to retrieve node list via API. status ({})\n'.format(node_list_rsp.status)
        return []

    # Select node by node type and SKU
    for node_entry in node_list:
        if node_id and node_id == node_entry['id']:
            # check if user specified a single node_id to run against
            # user must know the node_id and any check for a valid node_id is skipped
            node_id_list = [node_id]
            break
        elif obm_mac == 'all':
            # We are searching for all nodes with the requested sku
            if sku_name == 'all':
                # Select only managed compute nodes
                if node_type == 'all' or node_entry['type'] == node_type:
                    if not validate_obm or validate_obm_settings(client, node_entry['id']):
                        node_id_list.append(node_entry['id'])
            else:
                if node_entry.get('sku') and sku_id in node_entry['sku']:
                    if not validate_obm or validate_obm_settings(client, node_entry['id']):
                        node_id_list.append(node_entry['id'])
        else:
            # we are looking for a particular node with the requested OBM MAC
            Api().nodes_get_obms_by_node_id(identifier=node_entry['id'])
            obm_list_rsp = client.last_response
            obm_list = loads(obm_list_rsp.data)

            # Determine if the list was obtained without error
            if obm_list_rsp.status != 200:
                # There is no chance of getting the requested obm object using this node id, just 
                # try another node.
                print '**** Unable to retrieve obm list via API for node: {} status: ({}).\n'.format(node_entry['id'],
                                                                                                     obm_list_rsp.status)
                continue

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
    if verbosity >= 3:
        print "Node ID List:"
        if node_id_list:
            print node_id_list, '\n'
        else:
            print '**** Empty node ID list.\n'
    return node_id_list


def validate_obm_settings(client, identifier):
    """
    The OBM objectis are obtained for the requested node. They are then searched to 
    determine if at least one has OBM settings.
    :param  client: reference to config.api2_0_config
    :param  identifier: ID of node object
    return: True  - node have OBM setting
            False - node does not have OBM settings
    """

    Api().nodes_get_obms_by_node_id(identifier=identifier)
    obm_list_rsp = client.last_response
    obm_list = loads(obm_list_rsp.data)

    # Determine if the list was obtained without error
    if obm_list_rsp.status != 200:
        # There is no chance of getting the requested obm object using this node id, just 
        # return False to indicate no OBM settings
        print '**** Unable to retrieve obm list via API for node:: {} status: ({}).\n'.format(identifier,
                                                                                              obm_list_rsp.status)
        return False

    # determine if this node possible credentials 
    # TODO: additional tests may be required
    for obm_entry in obm_list:
        if get_by_string(obm_entry, 'config.user'):
            return True
        if get_by_string(obm_entry, 'config.properties.community'):
            return True
    return False
    
def get_by_string(source_dict, search_string, default_if_not_found=None):
    '''
    Search a dictionary using keys provided by the search string.
    The search string is made up of keywords separated by a '.'
    Example: 'fee.fie.foe.fum'
    :param source_dict: the dictionary to search
    :param search_string: search string with keyword separated by '.'
    :param default_if_not_found: Return value if search is un-successful
    :return value, dictionary or default_if_not_found
    ''' 
    if not source_dict or not search_string:
        return default_if_not_found

    dict_obj = source_dict

    for search_key in search_string.split("."):
        try:
            dict_obj = next(val for key, val in dict_obj.iteritems() if key == search_key)
        except StopIteration:
            return default_if_not_found
    return dict_obj
        