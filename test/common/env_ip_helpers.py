"""
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Module to hold helper classes and functions to determine run-time test IP
information. Currently,
"""
import flogging
import ipaddress
import netifaces
import socket
import fit_common

logs = flogging.get_loggers()


class TestHostInterfacer(object):
    _cached = None

    @classmethod
    def get_testhost_ip(cls):
        if cls._cached is None:
            cls._cached = cls()
            logs.info('The IP address of %s has been selected as the most likely testhost IP address reachable from the DUT',
                      cls._cached.__alleged_testhost_ip)
        return cls._cached.__alleged_testhost_ip

    def __init__(self):
        self.__alleged_testhost_ip = None

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = fit_common.fitargs()['rackhd_host']
        monip = fit_common.fitcfg()["rackhd-config"]["apiServerAddress"]
        monip_obj = ipaddress.ip_address(monip)
        logs.irl.debug('Trying to determine testhost IP address. Hitting rackhd_host value %s first', ip)
        s.connect((ip, 0))
        logs.debug('  ip used to generate connection to %s was %s: ', ip, s.getsockname()[0])
        alleged_testhost_ip_str = s.getsockname()[0]
        # python2/3 flake handling. The 'unicode' keyword is gone from p3. However, although
        # our code is p2, hound uses p3. We can cover both by using the -type- of a unicode string!
        ucode_type = type(u'unicode_string_to_type')
        alleged_testhost_ip = ipaddress.ip_address(ucode_type(alleged_testhost_ip_str))
        if not alleged_testhost_ip.is_loopback:
            # A non-loopback address is about the best guess we can get. Use it.
            logs.irl.debug('  ip used to generate connection to %s is non-loopback. Using %s', ip, alleged_testhost_ip_str)
            self.__alleged_testhost_ip = alleged_testhost_ip_str
            return

        # Localhost. Great. We are either running on the DUT or are on a test-host.
        # In either case, grabbing pretty much any ip interface that isn't a loop back
        # should do the trick.
        docker_net = []
        mono_net = []
        eform_net = []
        vbox_net = []
        veth_net = []
        extras_net = []
        int_list = netifaces.interfaces()
        for interface in int_list:
            logs.irl.debug('  checking interface %s', interface)
            ifaddrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET not in ifaddrs:
                logs.irl.debug('   -- no ifaddrs on it, skipping')
            else:
                for net in ifaddrs[netifaces.AF_INET]:
                    logs.irl.debug('    checking %s on %s', net, interface)
                    addr = net['addr']
                    mask = net['netmask']
                    inet_form = u'{}/{}'.format(addr, mask)
                    this_iface = ipaddress.ip_interface(inet_form)
                    this_iface.on_name = interface
                    dispo = None
                    if this_iface.is_loopback:
                        dispo = 'loopback-skip'
                    elif monip_obj in this_iface.network:
                        # really the last choice, all things considered!
                        dispo = 'added to control-network-list'
                        mono_net.append(this_iface)
                    elif 'docker' in interface:
                        dispo = 'added to docker list'
                        docker_net.append(this_iface)
                    elif interface.startswith('vbox'):
                        dispo = 'added to vbox list'
                        vbox_net.append(this_iface)
                    elif interface.startswith('veth'):
                        dispo = 'added to veth list'
                        veth_net.append(this_iface)
                    elif interface.startswith('eth') or interface.startswith('en'):
                        dispo = 'added to en/eth list'
                        eform_net.append(this_iface)
                    else:
                        logs.irl.debug('unknown interface type-ish %s seen', interface)
                        dispo = 'added to extras list'
                        extras_net.append(this_iface)
                    logs.irl.debug('     -> %s', dispo)

        ordered_list = []
        ordered_list.extend(eform_net)
        ordered_list.extend(docker_net)
        ordered_list.extend(vbox_net)
        ordered_list.extend(veth_net)
        ordered_list.extend(extras_net)
        ordered_list.extend(mono_net)
        logs.irl.debug('  Final list of possible addresses: %s', ordered_list)
        # note: we could go and ssh over and ping back to check these. For now, just
        # grab the first.
        if len(ordered_list) == 0:
            logs.warning('could not find the test-host ip address and fell back on localhost')
            self.__alleged_testhost_ip = '127.0.1.1'
            return
        picked = ordered_list[0]
        logs.irl.debug('picked %s on %s', picked.ip, picked.on_name)
        self.__alleged_testhost_ip = str(picked.ip)


def get_testhost_ip():
    return TestHostInterfacer.get_testhost_ip()
