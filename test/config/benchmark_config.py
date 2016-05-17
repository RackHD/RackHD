from settings import *

def set_ansible_auth(local_user, local_pwd, host_ssh_port, host_ssh_user, host_ssh_pwd, img_srv):
    set_b64_cred({"LOCAL_USER":local_user, "LOCAL_PWD":local_pwd, "HOST_SSH_PORT":host_ssh_port, \
                  "HOST_SSH_USER": host_ssh_user, "HOST_SSH_PWD": host_ssh_pwd, \
                  "IMAGE_SERVER": img_srv})

def get_ansible_auth():
    return get_b64_cred(['LOCAL_USER', 'LOCAL_PWD', 'HOST_SSH_PORT', \
                        'HOST_SSH_USER', 'HOST_SSH_PWD'])

def get_image_server():
    return get_b64_cred(['IMAGE_SERVER'])

# Initial ansible auth information if it doesn't exist
try:
    get_ansible_auth()
except:
    local_user = raw_input('localhost username: ')
    local_pwd = getpass('localhost sudo password: ')
    host_ssh_port = raw_input('RackHD ssh port (22): ')
    host_ssh_user = raw_input('RackHD ssh username (onrack): ')
    host_ssh_pwd = getpass('RackHD ssh password (onrack): ')
    img_srv = raw_input('image server - used in bootstrap: ')

    host_ssh_port = "22" if host_ssh_port == "" else host_ssh_port
    host_ssh_user = "onrack" if host_ssh_user == "" else host_ssh_user
    host_ssh_pwd = "onrack" if host_ssh_pwd == "" else host_ssh_pwd

    set_ansible_auth(local_user, local_pwd, host_ssh_port, host_ssh_user, host_ssh_pwd, img_srv)
