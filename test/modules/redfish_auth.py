from config.redfish1_0_config import config
from config.auth import *
from config.settings import *
from logger import Log
from json import loads, dumps
import pexpect
import pxssh

LOG = Log(__name__)

class Auth(object):
    """
    Class to abstract python authentication functionality
    """
    @staticmethod
    def get_auth_token():
        """ call /SessionService/Sessions to get auth_token """
        resource_path = '/redfish/v1/SessionService/Sessions'
        method = 'POST'
        body_params = {
            'UserName': 'admin',
            'Password': 'admin123'
        }
        config.api_client.host = config.host_authed
        config.api_client.call_api(resource_path, method, body=body_params)
        return config.api_client.last_response.getheader('X-Auth-Token')

    @staticmethod
    def local_host_exception_setup():
        """ Attempt to add a user using localhost exception """
        param = dumps({'username': 'admin', 'password': 'admin123', 'role': 'Administrator'})
        user_add_cmd = "curl -k -X POST -w '%{http_code}' -H 'Content-Type: application/json' -d '"
        user_add_cmd += param
        user_add_cmd += "' https://127.0.0.1:" + USER_AUTH_PORT + "/api/2.0/users"

        term = pxssh.pxssh()
        term.SSH_OPTS = (term.SSH_OPTS
                         + " -o 'StrictHostKeyChecking=no'"
                         + " -o 'UserKnownHostsFile=/dev/null' ")
        term.force_password = True
        term.login(HOST_IP, SSH_USER, SSH_PASSWORD, port=SSH_PORT)
        term.sendline(user_add_cmd)
        index = term.expect(['201', '401', '403'], 10)
        if index == 0:
            LOG.info('Created default user')
        if index == 1 or index == 2:
            LOG.info('Local user already created')
        term.logout()
        return index

    @staticmethod
    def enable():
        """ update config to enable auth """
        if config.auth_enabled:
            LOG.info('auth already enabled.')
        Auth.local_host_exception_setup()
        config.api_client.default_headers['X-Auth-Token'] = Auth.get_auth_token()
        config.api_client.host = config.host_authed + config.api_root
        config.auth_enabled = True
        LOG.info('Enable auth successfully.')

    @staticmethod
    def disable():
        """ update config to disable auth """
        if not config.auth_enabled:
            LOG.info('auth already disabled.')
        del config.api_client.default_headers['X-Auth-Token']
        config.api_client.host = config.host + config.api_root
        config.auth_enabled = False
        LOG.info('Disable auth successfully.')
