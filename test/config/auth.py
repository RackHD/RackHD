import os

SSH_USER = os.getenv('RACKHD_SSH_USER', 'vagrant')
SSH_PASSWORD = os.getenv('RACKHD_SSH_PASSWORD', 'vagrant')
SSH_PORT = os.getenv('RACKHD_SSH_PORT', '2222')
USER_AUTH_PORT = os.getenv('RACKHD_USER_AUTH_PORT', '8443')
