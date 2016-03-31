from settings import *

ANSIBLE_AUTH_FILE = '.ansible_auth'

# Obfuscate credentials
def set_ansible_auth(local_user, local_pwd, host_ssh_port, host_ssh_user, host_ssh_pwd):
    lu = b64encode(local_user)
    lp = b64encode(local_pwd)
    rport = b64encode(host_ssh_port)
    ru = b64encode(host_ssh_user)
    rp = b64encode(host_ssh_pwd)

    with open(ANSIBLE_AUTH_FILE,'w+') as file:
        out = \
        'local_user="{0}"\n'.format(lu) + \
        'local_pwd="{0}"\n'.format(lp) + \
        'host_ssh_port="{0}"\n'.format(rport) + \
        'host_ssh_user="{0}"\n'.format(ru) + \
        'host_ssh_pwd="{0}"\n'.format(rp)
        file.write(out)

# Unobfuscate credentials
def get_ansible_auth():
    ansible_auth = load_source('creds',ANSIBLE_AUTH_FILE)
    return b64decode(ansible_auth.local_user), b64decode(ansible_auth.local_pwd), \
        b64decode(ansible_auth.host_ssh_port), b64decode(ansible_auth.host_ssh_user), \
        b64decode(ansible_auth.host_ssh_pwd)

# Initial ansible auth file if it doesn't exist
if os.path.isfile(ANSIBLE_AUTH_FILE) is False:
    local_user = raw_input('localhost username: ')
    local_pwd = getpass('localhost sudo password: ')
    host_ssh_port = raw_input('RackHD ssh port (22): ')
    host_ssh_user = raw_input('RackHD ssh username (onrack): ')
    host_ssh_pwd = getpass('RackHD ssh password (onrack): ')

    host_ssh_port = "22" if host_ssh_port == "" else host_ssh_port
    host_ssh_user = "onrack" if host_ssh_user == "" else host_ssh_user
    host_ssh_pwd = "onrack" if host_ssh_pwd == "" else host_ssh_pwd

    set_ansible_auth(local_user, local_pwd, host_ssh_port, host_ssh_user, host_ssh_pwd)
