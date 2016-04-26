from imp import load_source
from getpass import getpass
from base64 import b64encode, b64decode
import logging
import os

HOST_IP = os.getenv('RACKHD_HOST','localhost')
HOST_PORT = os.getenv('RACKHD_PORT','9090')
HOST_PORT_AUTH = os.getenv('RACKHD_PORT_AUTH','9093')
HTTPD_PORT = os.getenv('RACKHD_HTTPD_PORT', '9010')

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
LOGGER_LVL = os.getenv('RACKHD_TEST_LOGLVL', 'WARNING')
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

def get_bmc_cred():
    return get_b64_cred(["BMC_USER", "BMC_PASS"])

# Initial cred file to log bmc password information if it doesn't exist
if os.path.isfile(CRED_FILE) is False:
    bmc_user = raw_input('BMC username: ')
    bmc_pass = getpass('BMC password: ')
    set_b64_cred({"BMC_USER":bmc_user, "BMC_PASS":bmc_pass})
