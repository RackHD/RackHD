from on_http import Configuration
from on_http import ApiClient
from imp import load_source
from getpass import getpass
from base64 import b64encode, b64decode
import logging
import os

API_VERSION = '1.1'

HOST_IP = os.getenv('RACKHD_HOST','localhost')
HOST_PORT = os.getenv('RACKHD_PORT','9090')
NODE_COUNT = int(os.getenv('RACKHD_NODE_COUNT', '2'))
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

# API client configuration
config = Configuration()
config.host = 'http://{0}:{1}'.format(HOST_IP,HOST_PORT)
config.verify_ssl = False
config.api_client = ApiClient(host=config.host)
config.debug = False
config.logger_format = LOGFORMAT
for key,elem in config.logger.iteritems():
    elem.setLevel(LOGLEVELS[LOGGER_LVL])

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
    BMC_USER = raw_input('BMC username: ')
    BMC_PASS = getpass('BMC password: ')
    set_bmc_cred(BMC_USER,BMC_PASS)

