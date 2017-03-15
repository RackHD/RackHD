'''
Copyright 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

Author(s):
George Paulos

This is a FIT common library containing network helper routines to perform
commonly-used network-related functions
'''

import fit_path  # NOQA: unused import
import fit_common
import flogging
log = flogging.get_loggers()


def get_host_nics(host=fit_common.fitargs()['rackhd_host']):
    """
    This routine returns an array of valid network ports on the specified host, default rackhd_host
    """
    # collect nic names
    getifs = fit_common.remote_shell("ifconfig -s -a |tail -n +2 |grep -v -e Iface -e lo -e docker", host)
    # split into array
    splitifs = getifs['stdout'].split('\n')
    niclist = []  # array of valid network ports
    # clean out login artifacts and verify ports
    for item in splitifs:
        if "assword" not in item and item.split(" ")[0]:
            if fit_common.remote_shell("ifconfig -s " + item.split(" ")[0])['exitcode'] == 0:
                niclist.append(item.split(" ")[0])
    return niclist


def split_ipv4(ipaddress=None):
    """
    This routine splits a valid IPv4 address or netmask into decimal octets
    and verifies that the address is valid IPv4
    then returns a 4-element array of octets
    """
    if not ipaddress:
        return None
    iparray = ipaddress.split(".")
    if len(iparray) != 4:
        log.error("Invalid IP address: " + ipaddress)
        return None
    for octet in iparray:
        if int(octet) < 0 or int(octet) > 255:
            log.error("Invalid IP address: " + ipaddress)
            return None
    return iparray


def nic_config_file(iface=None, ipaddress=None, netmask="255.255.255.0", gateway=None):
    """
    This routine creates a NIC config file string from the specified NIC port, IP address, netmask, etc.
    """
    config_string = ""
    if iface:
        config_string = "auto " + iface + "\n" + \
                        "iface " + iface + " inet static\n"
    else:
        return None  # return None if no iface specified
    if ipaddress:
        config_string = config_string + "ipaddress " + ipaddress + "\n"
        config_string = config_string + "netmask " + netmask + "\n"
    else:
        config_string = "auto " + iface + "\n" + \
                        "iface " + iface + " inet dhcp\n"
        return config_string  # return DHCP if no ipaddress specified
    if gateway:
        config_string = config_string + "gateway " + gateway + "\n"
    return config_string


def dhcp_config_file(ipaddress=None, netmask="255.255.255.0", default_lease_time=600, max_lease_time=7200):
    """
    This routine creates a DHCP config file string that is composed
    from the DHCP server IP address and netmask and other optional params
    """
    if not ipaddress or not split_ipv4(ipaddress) or not split_ipv4(netmask):
        return None  # return None if ipaddress is missing or invalid
    ipsplit = split_ipv4(ipaddress)
    ip_prefix = ipsplit[0] + '.' + ipsplit[1] + '.' + ipsplit[2] + '.'
    masksplit = split_ipv4(netmask)
    dhcp_high = \
        str(int(ipsplit[0]) + (255 - int(masksplit[0]))) + '.' + \
        str(int(ipsplit[1]) + (255 - int(masksplit[1]))) + '.' + \
        str(int(ipsplit[2]) + (255 - int(masksplit[2]))) + '.' + '254'
    dhcp_low = ip_prefix + str(int(ipsplit[3]) + 2)
    config_string = 'ddns-update-style none;\n' \
                    'option domain-name "example.org";\n' \
                    'option domain-name-servers ns1.example.org, ns2.example.org;\n' \
                    'default-lease-time ' + str(default_lease_time) + ';\n' \
                    'max-lease-time ' + str(max_lease_time) + ';\n' \
                    'log-facility local7;\n' \
                    'deny duplicates;\n' \
                    'ignore-client-uids true;\n' \
                    'subnet ' + ip_prefix + '0 netmask ' + fit_common.fitrackhd()['dhcpSubnetMask'] + ' {\n' \
                    '  range ' + dhcp_low + ' ' + dhcp_high + ';\n' \
                    '  option vendor-class-identifier "PXEClient";\n' \
                    '}\n'
    return config_string


def verify_rackhd_network_config():
    """
    This routine verifies network configuration settings in rackhd_default.json file
    Checks for required parameters and verifies that IP addresses are valid
    Returns True for valid and False for invalid, details in error log
    """
    status = True
    config_keys = ["dhcpGateway",
                   "dhcpSubnetMask",
                   "dhcpProxyBindAddress",
                   "apiServerAddress",
                   "gatewayaddr",
                   "subnetmask",
                   "broadcastaddr",
                   "tftpBindAddress",
                   "syslogBindAddress"]
    for item in config_keys:
        if item not in fit_common.fitrackhd():
            log.error("Key missing in rackhd_default.json: " + item)
            status = False
        if item in fit_common.fitrackhd() and not split_ipv4(fit_common.fitrackhd()[item]):
            log.error("Invalid " + item + " address in rackhd_default.json: " + fit_common.fitrackhd()[item])
            status = False
    return status
