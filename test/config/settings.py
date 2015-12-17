from imp import load_source
from getpass import getpass
from base64 import b64encode, b64decode
import logging
import os

API_VERSION = '1.1'

# CRITICAL < ERROR < WARNING < INFO < DEBUG
LOGLEVEL = os.getenv('RACKHD_TEST_LOGLVL', 'WARNING')
LOGFMT = '%(asctime)s:%(name)s:%(levelname)s - %(message)s'

HOST_IP = os.getenv('RACKHD_HOST','localhost')
HOST_PORT = os.getenv('RACKHD_PORT','9090')
CRED_FILE = '.passwd'

# Obfuscate credentials
def set_bmc_cred(user,password):
    u = b64encode(user)
    p = b64encode(password)
    with open(CRED_FILE,'w+') as file:
        out = \
        'BMC_USER="{0}"\n'.format(u) + \
        'BMC_PASS="{0}"'.format(p)
        file.write(out)

# Unobfuscate credentials
def get_bmc_cred():
    creds = load_source('creds',CRED_FILE)
    return b64decode(creds.BMC_USER), b64decode(creds.BMC_PASS)

# Initial bmc passwd file if it doesn't exist
if os.path.isfile(CRED_FILE) is False:
    if 0 == len(DEFAULT_BMC_USER) and 0 == len(DEFAULT_BMC_PASS):
        DEFAULT_BMC_USER = raw_input('BMC username: ')
        DEFAULT_BMC_PASS = getpass('BMC password: ')
    set_bmc_cred(DEFAULT_BMC_USER,DEFAULT_BMC_PASS)
