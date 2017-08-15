from imp import load_source
from getpass import getpass
from base64 import b64encode, b64decode

# Obfuscate credentials
ANSIBLE_CRED_FILE = '.ansible_config'
ANSIBLE_KEY = []


def set_ansible_auth(creds):
    out = ''
    with open(ANSIBLE_CRED_FILE, 'a+') as file:
        for (k, v) in creds.items():
            new_v = b64encode(v)
            out += '{0}="{1}"\n'.format(k, new_v)
        file.write(out)

def get_ansible_auth():
    creds = load_source('creds', ANSIBLE_CRED_FILE)
    req = [
        "LOCAL_USER", "LOCAL_PWD", "RACKHD_IP",
        "SSH_PORT", "SSH_USER", "SSH_PWD"
    ]
    rsp = []
    for key in req:
        rsp.append(b64decode(getattr(creds, key)))
    if len(rsp) != len(req):
        rsp = [None, None]
    return rsp

# Initial ansible auth information if it doesn't exist
try:
    get_ansible_auth()
except:
    local_user = raw_input('localhost username: ')
    local_pwd = getpass('localhost sudo password: ')
    rackhd_ip = raw_input('rackhd ip: ')
    rackhd_ssh_port = raw_input('rackhd ssh port: ')
    rackhd_ssh_user = raw_input('rackhd username: ')
    rackhd_ssh_pwd = getpass('rackhd password: ')
    creds = {
        "LOCAL_USER": local_user,
        "LOCAL_PWD": local_pwd,
        "RACKHD_IP": rackhd_ip,
        "SSH_PORT": rackhd_ssh_port,
        "SSH_USER": rackhd_ssh_user,
        "SSH_PWD": rackhd_ssh_pwd
    }
    set_ansible_auth(creds)
