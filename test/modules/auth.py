from config.api1_1_config import *
from logger import Log
from json import loads

LOG = Log(__name__)

class Auth(object):
    """
    Class to abstract python authentication functionality
    """
    def get_auth_token(self):
        """ call /login to get auth_token """
        resource_path = '/login'
        method = 'POST'
        body_params = {
            'username': 'admin',
            'password': 'admin123'
        }
        config.api_client.call_api(resource_path, method, body=body_params)
        token_blob = loads(config.api_client.last_response.data)
        LOG.debug(token_blob, json=True)
        return token_blob['token']

    def enable(self):
        """ update config to enable auth """
        if config.auth_enabled:
            LOG.info('auth already enabled.')
        config.api_client_no_auth = config.api_client
        config.api_client = config.api_client_authed
        config.api_key = {'authorization' : self.get_auth_token()}
        config.api_key_prefix = {'authorization' : 'JWT'}
        config.auth_enabled = True
        LOG.info('Enable auth successfully.')

    def disable(self):
        """ update config to disable auth """
        if not config.auth_enabled:
            LOG.info('auth already disabled.')
        config.api_client_authed = config.api_client
        config.api_client = config.api_client_no_auth
        del config.api_client_no_auth
        config.api_key = {}
        config.api_key_prefix = {}
        config.auth_enabled = False
        LOG.info('Disable auth successfully.')
