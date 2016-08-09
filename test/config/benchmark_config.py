from settings import *

def set_ansible_auth(local_user, local_pwd):
    set_b64_cred({"LOCAL_USER":local_user, "LOCAL_PWD":local_pwd})

def get_ansible_auth():
    return get_b64_cred(['LOCAL_USER', 'LOCAL_PWD'])

# Initial ansible auth information if it doesn't exist
try:
    get_ansible_auth()
except:
    local_user = raw_input('localhost username: ')
    local_pwd = getpass('localhost sudo password: ')
    set_ansible_auth(local_user, local_pwd)
