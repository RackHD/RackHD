from imp import load_source
from getpass import getpass
from base64 import b64encode, b64decode
import logging
import json
import os, sys
import ConfigParser

# Check for fit-based configuration
CONFIG = os.environ.get('FIT_CONFIG', None)
if CONFIG:
    # Load FIT configuration (.json format)
    import fit_common

    defaults = fit_common.fitcfg()['cit-config']
    defaults['RACKHD_HOST'] = fit_common.fitcfg()['rackhd_host']
    defaults['RACKHD_PORT'] = fit_common.fitports()['http']
    defaults['RACKHD_PORT_AUTH'] = fit_common.fitports()['https']
    #defaults['RACKHD_USER_AUTH_PORT'] = fit_common.fitports()['https']
    defaults['RACKHD_HTTPD_PORT'] = fit_common.fitports()['httpd']
    defaults['RACKHD_SSH_PORT'] = fit_common.fitports()['ssh']
    defaults['RACKHD_SSH_USER'] = fit_common.fitcreds()['rackhd_ssh'][0]['username']
    defaults['RACKHD_SSH_PASSWORD'] = fit_common.fitcreds()['rackhd_ssh'][0]['password']
    defaults['RACKHD_SMB_USER'] = fit_common.fitcreds()['rackhd_smb'][0]['username']
    defaults['RACKHD_SMB_PASSWORD'] = fit_common.fitcreds()['rackhd_smb'][0]['password']
    defaults['RACKHD_AMQP_URL'] = fit_common.fitrackhd()['amqp']

    # map from original cit repo path name to httpProxies in rackhd configuration
    mappings = {
        'RACKHD_CENTOS_REPO_PATH': '/CentOS/6.5',
        'RACKHD_ESXI_REPO_PATH': '/ESXi/6.0',
        'RACKHD_UBUNTU_REPO_PATH': '/Ubuntu/14'
    }
    for cit_path, local_path in mappings.items():
        server_path = None
        for proxy in fit_common.fitrackhd()['httpProxies']:
            if local_path == proxy['localPath']:
                server_path = proxy['server']
                break
        if server_path:
            defaults[cit_path] = server_path

else:
    # Load CIT configuration (.ini format)
    CONFIG = 'config/config.ini'
    for v in sys.argv:
        if 'config' in v:
            CONFIG = v.split('=')[1:]
    config_parser = ConfigParser.RawConfigParser()
    config_parser.read(CONFIG)
    defaults = {}
    for k,v in config_parser.items('DEFAULT'):
        defaults[k.upper()] = v

HOST_IP = defaults['RACKHD_HOST']
HOST_PORT = defaults['RACKHD_PORT']
HOST_PORT_AUTH = defaults['RACKHD_PORT_AUTH']
HTTPD_PORT = defaults['RACKHD_HTTPD_PORT']

CRED_FILE = '.passwd'

# Global logger setup: CRITICAL < ERROR < WARNING < INFO < DEBUG
LOGFORMAT = '%(asctime)s:%(name)s:%(levelname)s - %(message)s'
LOGLEVELS = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG
}
LOGGER_LVL = defaults['RACKHD_TEST_LOGLVL']
logging.basicConfig(level=LOGLEVELS[LOGGER_LVL], format=LOGFORMAT)

# Obfuscate credentials
def set_b64_cred(cred):
    out = ''
    with open(CRED_FILE,'a+') as file:
        for (k, v) in cred.items():
            new_v = b64encode(v)
            out += '{0}="{1}"\n'.format(k, new_v)
        file.write(out)

# Unobfuscate credentials
def get_b64_cred(req):
    creds = load_source('creds',CRED_FILE)
    rsp = []
    for key in req:
        rsp.append(b64decode(getattr(creds, key)))
    if len(rsp) != len(req):
        rsp = [None, None]
    return rsp

def get_cred(service):
    if service == 'bmc':
        return get_b64_cred(["BMC_USER", "BMC_PASS"])
    elif service == 'redfish':
        return get_b64_cred(["REDFISH_USER", "REDFISH_PASS"])
    else:
        return None

def get_bmc_cred():
    return get_cred('bmc')

# Initial cred file to log bmc password information if it doesn't exist
if os.path.isfile(CRED_FILE) is False:
    bmc_user = raw_input('BMC username: ')
    bmc_pass = getpass('BMC password: ')
    redfish_user = raw_input('Redfish username: ')
    redfish_pass = getpass('Redfish password: ')
    creds = {
        "BMC_USER":bmc_user, 
        "BMC_PASS":bmc_pass,
        "REDFISH_USER":redfish_user, 
        "REDFISH_PASS":redfish_pass
    }
    set_b64_cred(creds)
    

