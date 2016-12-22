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
    with open(CONFIG) as config_file:
        config_blob = json.load(config_file)
        defaults = config_blob['cit-config']
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
    

