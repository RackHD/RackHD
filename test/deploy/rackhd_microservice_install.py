'''
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

This script installs the microservices packages on top of a running RackHD in the Minnesota lab.
In this script, we have a callback URI port which we have hard-coded to 9080. Change this port value as
per your requirements.
If test bed is behind proxy wall, make sure to enter proxy URL in config/install_default.json
This script performs the following functions:
    - loads prerequisite packages docker
    - loads prerequisite packages docker-compose
    - downloads RackHD dell microservices packages
    - installs using docker
    - load configuration files
    - startup and verify operations

usage:
    python run_tests.py -stack <stack ID> -test deploy/rackhd_microservice_install.py
'''

import fit_path  # NOQA: unused import
import fit_common
import flogging
import os
import socket
import time
import unittest
from nosedep import depends

logs = flogging.get_loggers()

# sets up proxy if required
PROXYVARS = ''
if fit_common.fitproxy()['host'] != '':
    # note that both proxy server settings below are set to the same http: URL
    PROXYVARS = "export http_proxy=http://" + fit_common.fitproxy()['host'] + ":" + fit_common.fitproxy()['port'] + ";" + \
                "export https_proxy=http://" + fit_common.fitproxy()['host'] + ":" + fit_common.fitproxy()['port'] + ";"


class rackhd_micro_install(unittest.TestCase):
    def test00_check_env(self):
        # checks the version of Ubuntu as the deploy script is specific to 14.04
        command = "cat /etc/lsb-release | grep 14.04"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0,
                         "This is not Ubuntu 14.04 version. So the deploy script wont work")

    @depends(after=test00_check_env)
    def test01_update_sudoers_info(self):
        # update sudoers to preserve proxy environment
        logs.info(" ***** Update sudoers proxy env ****")
        sudoersproxy = open("sudoersproxy", 'w')
        sudoersproxy.write('Defaults env_keep="HOME http_proxy https_proxy ftp_proxy"\n')
        sudoersproxy.close()
        fit_common.remote_shell('pwd')
        fit_common.scp_file_to_ora("sudoersproxy")
        self.assertEqual(fit_common.remote_shell('cp sudoersproxy /etc/sudoers.d/'
                                                 )['exitcode'], 0, "sudoersproxy config failure.")
        os.remove('sudoersproxy')

    @depends(after=test00_check_env)
    def test02_add_nfs_mount(self):
        logs.info(" ***** Add NFS mount point ****")
        self.assertEqual(fit_common.remote_shell(PROXYVARS + "apt-get -y install nfs-kernel-server")['exitcode'],
                         0, "nfs-kernel-server install failure.")
        nfsexports = open("nfsexports", 'w')
        nfsexports.write('/nfs               *(rw,sync,no_subtree_check,no_root_squash,no_all_squash)\n')
        nfsexports.close()
        fit_common.scp_file_to_ora("nfsexports")

        # Making a backup copy of /etc/exports file
        rc = fit_common.remote_shell('test -e /etc/microservices_exports.bak')

        if rc['exitcode'] == 0:
            fit_common.remote_shell('cp /etc/microservices_exports.bak /etc/exports')
        else:
            fit_common.remote_shell('cp /etc/exports /etc/microservices_exports.bak')

        self.assertEqual(fit_common.remote_shell('cat nfsexports >> /etc/exports'
                                                 )['exitcode'], 0, "nfsexports config failure.")

        # Make an nfs mount point
        self.assertEqual(fit_common.remote_shell('sudo mkdir -p /nfs'
                                                 )['exitcode'], 0, "Failed to mkdir /nfs")
        # Ubuntu 14.04 nfs services
        self.assertEqual(fit_common.remote_shell('sudo service nfs-kernel-server start'
                                                 )['exitcode'], 0, "Failed to start nfs-kernel-server")
        # export file system
        self.assertEqual(fit_common.remote_shell('sudo exportfs -a'
                                                 )['exitcode'], 0, "Failed on command exportfs -a")
        # check mount point
        self.assertEqual(fit_common.remote_shell('sudo showmount -e 172.31.128.1'
                                                 )['exitcode'], 0, "Display exported fs")

    @depends(after=test00_check_env)
    def test03_install_docker(self):
        # Check if docker-compose is already installed
        rsp = fit_common.remote_shell("docker -v")
        if rsp['exitcode'] == 0:
            logs.info(" Docker already installed")
            if "Docker version" in rsp['stdout']:
                logs.info(" Docker installed: %s", rsp['stdout'])
        else:
            logs.info(" Install Docker")

            # apt-get update
            command = PROXYVARS + "sudo apt-get update"
            self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "get-update failed.")

            # Getting the docker installation file from docker.com
            command = PROXYVARS + "sudo wget -qO- https://get.docker.com/ | sh"
            self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "Getting docker file from docker.com failed.")

            # Checking the users with whoami command
            command = "sudo usermod -aG docker $(whoami)"
            self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "whoami command failed.")

        # Check if docker-compose is already installed
        rsp = fit_common.remote_shell("docker-compose -v")
        if rsp['exitcode'] == 0:
            logs.info(" docker-compose already installed")
            if "docker-compose version" in rsp['stdout']:
                logs.info(" Docker installed: %s", rsp['stdout'])
        else:
            # Installing python pip
            command = PROXYVARS + "sudo apt-get -y install python-pip"
            self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "Pip install failed.")

            # Installing docker compose
            logs.info(" Install docker-compose")
            command = PROXYVARS + "sudo pip install docker-compose"
            self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "Docker compose install failed.")

        # Setup docker proxy environment
        logs.info(" Setup Docker Proxy")
        dockerproxy = open("dockerproxy", 'w')
        # dockerproxy.write('export http_proxy="http://web.hwimo.lab.emc.com:3128/"\n')
        dockerproxy.write(PROXYVARS)
        dockerproxy.close()
        fit_common.scp_file_to_ora("dockerproxy")
        self.assertEqual(fit_common.remote_shell('cat dockerproxy >> /etc/default/docker'
                                                 )['exitcode'], 0, "adding docker proxy config failed.")
        os.remove('dockerproxy')

        # Restart the docker service
        command = PROXYVARS + "sudo service docker restart"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "Docker service restart failed.")
        time.sleep(60)

    @depends(after=test00_check_env)
    def test04_setup_rackhd_docker_services(self):
        # add the .env variables for HOST IP into the ".env" file
        envfile = open("envfile", 'w')
        envfile.write("TAG=latest\n")
        envfile.write("REGISTRY_IP=172.31.128.1\n")
        host_ip = "HOST_IP=" + socket.gethostbyname(fit_common.fitcfg()['rackhd_host']) + "\n"
        envfile.write(host_ip)
        envfile.close()
        fit_common.scp_file_to_ora("envfile")
        self.assertEqual(fit_common.remote_shell('cp envfile /home/onrack/.env'
                                                 )['exitcode'], 0, "copy of env file failed.")
        os.remove('envfile')

        # Get the username and password from config-mn/credentials.json
        username = fit_common.fitcreds()['docker_hub'][0]['username']
        password = fit_common.fitcreds()['docker_hub'][0]['password']
        command = 'cd rackhd/docker/dell; sudo docker login --username=' + username + ' --password=' + password
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "Docker login failed.")

        # Docker up consul
        command = "cd rackhd/docker/dell; sudo docker-compose up -d consul"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "Docker up consul failed.")
        time.sleep(30)

        command = "cd rackhd/docker/dell; sudo chmod +x set_config.sh; sudo ./set_config.sh"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "set_config.sh failed.")

        # Docker up the rest of micro service containers
        command = "cd rackhd/docker/dell; sudo docker-compose up -d"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "docker-compose up failed.")
        time.sleep(180)

        # Set port to 8080 in smi config file
        port_var = fit_common.fitports()['http']
        command = "cd rackhd/docker/dell; sudo sed -i 's/9090/" + str(port_var) + "/g' set_rackhd_smi_config.sh"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "set_rackhd_smi_config.sh failed.")

        # Populates smi config file
        command = "cd rackhd/docker/dell; sudo ./set_rackhd_smi_config.sh"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "set_rackhd_smi_config.sh failed.")

        # Replace  callback Uri port from 9988 to 9080 in smi config file
        command = "cd /opt/monorail; sudo sed -i 's/9988/9080/g' smiConfig.json"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "Change port from 9988 to 9080 in smiConfig failed.")

        # Restart on-http service
        command = "sudo service on-http restart"
        self.assertEqual(fit_common.remote_shell(command)['exitcode'], 0, "failed to start on-http service.")


if __name__ == '__main__':
    fit_common.unittest.main()
