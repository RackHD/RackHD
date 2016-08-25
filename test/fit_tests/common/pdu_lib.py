'''
Copyright 2016, EMC, Inc.

Author(s):
Jeanne Ohren
George Paulos

This library is for controlling PDU functions from FIT tests.
Currently only supports ServerTech PDU

'''

from fit_common import *

# Servertech PDU control stuff
ORA_POWER_IP = '192.168.1.1'
ORA_POWER_NETMASK = '24'
ORA_POWER_BCAST = '192.168.1.255'
SERVERTECH_PDU_IP = '192.168.1.254'
SERVERTECH_PDU_COMMUNITY = GLOBAL_CONFIG['snmp']['community']
SERVERTECH_CONTROL_ACTION_OID = '.1.3.6.1.4.1.1718.3.2.3.1.11.1.1.'
SERVERTECH_CONTROL_STATUS_OID = '.1.3.6.1.4.1.1718.3.2.3.1.10.1.1.'
SERVERTECH_CONTROL_ACTION_MAPPER = {
    'on': '1',
    'off': '2',
    'reboot': '3'
}
SERVERTECH_CONTROL_STATUS_MAPPER = {
    '0': 'idleOff',
    '1': 'idleOn',
    '2': 'wakeOff',
    '3': 'wakeOn',
    '4': 'off',
    '5': 'on',
    '6': 'lockedOff',
    '7': 'lockedOn',
    '8': 'reboot',
    '9': 'shutdown',
    '10': 'pendOn',
    '11': 'pendOff',
    '12': 'minimumOff',
    '13': 'minimumOn',
    '14': 'eventOff',
    '15': 'eventOn',
    '16': 'eventReboot',
    '17': 'eventShutdown'
}

def check_pdu_type():
    # execute check_pdu_type() to return PDU type if available, else return 'Unknown'
    # check if PDU is defined in Stack dict
    if 'pdu' in  STACK_CONFIG[ARGS_LIST['stack']]:
        pduaddr = STACK_CONFIG[ARGS_LIST['stack']]['pdu']
    else:
        return "Unknown"
    if remote_shell('ping -c 1 ' + pduaddr)['exitcode'] == 0:
        if STACK_CONFIG[ARGS_LIST['stack']]['pdu'] == "192.168.1.254":
            return "ServerTech"
    return "Unknown"

def config_power_interface():
    # We need to access the PDU before OnRack is installed
    # Therefore, we need to temporarily configure the power interface

    # Check for existing power interface by pinging PDU
    if remote_shell('ping -c 1 192.168.1.254')['exitcode'] == 0:
        return True

    iflist = remote_shell("ifconfig -s -a | tail -n +2 | awk \\\'{print \\\$1}\\\' |grep -v lo")['stdout'].split()

    # eth3 is power port in bare-metal eth2 is power interface in VM
    if iflist[1] != "":
        power_if = iflist[8]
    else:
        print "Failed to find power interface"
        return False

    cmd = "ip addr add {0}/{1} broadcast {2} dev {3}".format(ORA_POWER_IP,
                                                             ORA_POWER_NETMASK,
                                                             ORA_POWER_BCAST,
                                                             power_if)
    response = remote_shell(cmd)

    if response['exitcode'] != 0:
        print "Failed to configure power interface {0}".format(power_if)
        return False

    response = remote_shell("ip link set {0} up".format(power_if))

    if response['exitcode'] != 0:
        print "Failed to set link up on interface {0}".format(power_if)
        return False

    return True

# We need snmp commands before OnRack is installed
def install_snmp():
    ENVVARS = ''
    if 'proxy' in GLOBAL_CONFIG['repos'] and GLOBAL_CONFIG['repos']['proxy'] != '':
        ENVVARS = "export http_proxy=" + GLOBAL_CONFIG['repos']['proxy'] + ";" + \
                  "export https_proxy=" + GLOBAL_CONFIG['repos']['proxy'] + ";"
    response = remote_shell(ENVVARS + 'apt-get -y install snmp')
    if response['exitcode'] != 0:
        print "Failed to install snmp"
        return False

    return True


# Control the PDU outlets for all compute nodes
# Assumes compute nodes are plugged into outlets 7-16 of a ServerTech PDU
def pdu_control_compute_nodes(state):

    stech_action = SERVERTECH_CONTROL_ACTION_MAPPER.get(state, None)
    if stech_action is None:
        print "Invalid power state: " + state
        return False

    # Make sure the power interface is up and active
    for i in range(0, 30):
        response = remote_shell("ping -c 1 -w 5 {0}".format(SERVERTECH_PDU_IP))
        if response['exitcode'] == 0:
            break
        countdown(2)

    if i == 29:
        print "Failed to access {0}".format(SERVERTECH_PDU_IP)
        return False

    all_set = True

    # Compute nodes are plugged into outlets 7-16
    for outlet in range(7, 17):
        cmd = "snmpset -v2c -c {0} {1} {2}{3} i {4}".format(SERVERTECH_PDU_COMMUNITY,
                                                            SERVERTECH_PDU_IP,
                                                            SERVERTECH_CONTROL_ACTION_OID,
                                                            outlet,
                                                            stech_action)
        response = remote_shell(cmd)

        if response['exitcode'] != 0:
            print "Failed to set state ({0}) for outlet ({1})".format(state,
                                                                      outlet)
            all_set = False
            continue

        # Verify that the state is set as expected
        cmd = "snmpget -v2c -c{0} {1} {2}{3}".format(SERVERTECH_PDU_COMMUNITY,
                                                     SERVERTECH_PDU_IP,
                                                     SERVERTECH_CONTROL_STATUS_OID,
                                                     outlet)
        get_response = remote_shell(cmd)['stdout'].split()
        status = get_response[9]

        status_str = SERVERTECH_CONTROL_STATUS_MAPPER.get(status, 'unknown')

        # Returned status should be either on/off or pendOn/pendOff
        pend_state = "pend" + state.title()
        if status_str != state and status_str != pend_state:
            print "Returned status ({0}) does not match state ({1}) for outlet {2}".format(status_str, state, outlet)
            all_set = False

    return all_set



