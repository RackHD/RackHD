'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo
This test validate the system level function of RackHD image-service. This test include VMware ESXi install and node
rediscover.It use image server to store ESXi image and microkernel used for RackHD discovery.
You need put an config file in the /config directory
'''

import os
import sys
import time
import flogging
import random
import fit_common
import urllib2
import pexpect
import unittest
import test_api_utils
from nose.plugins.attrib import attr
logs = flogging.get_loggers()


@attr(all=False, regression=False, smoke=False, imageservice=False)
class test_image_service_system(fit_common.unittest.TestCase):
    def _get_serverip(self):
        args = fit_common.fitargs()['unhandled_arguments']
        for arg in args:
            if "imageserver" in arg:
                serverip = arg.split("=")[1]
                return serverip

    def _apply_obmsetting_to_node(self, nodeid):
        usr = ''
        pwd = ''
        response = fit_common.rackhdapi(
            '/api/2.0/nodes/' + nodeid + '/catalogs/bmc')
        if response['status'] in range(200, 205):
            bmcip = response['json']['data']['IP Address']
        else:
            bmcip = "0.0.0.0"
        if bmcip == "0.0.0.0":
            response = fit_common.rackhdapi(
                '/api/2.0/nodes/' + nodeid + '/catalogs/rmm')
            bmcip = response['json']['data']['IP Address']
        # Try credential record in config file
        for creds in fit_common.fitcreds()['bmc']:
            if fit_common.remote_shell(
                'ipmitool -I lanplus -H ' + bmcip + ' -U ' +
                    creds['username'] + ' -P ' + creds['password'] + ' fru')['exitcode'] == 0:
                usr = creds['username']
                pwd = creds['password']
                break
        # Put the credential to OBM settings
        if usr != "":
            payload = {
                "service": "ipmi-obm-service",
                "config": {
                    "host": bmcip,
                    "user": usr,
                    "password": pwd},
                "nodeId": nodeid}
            api_data = fit_common.rackhdapi("/api/2.0/obms", action='put', payload=payload)
            if api_data['status'] == 201:
                return True
        return False

    def _upload_os_by_network(self, osname, osversion, source_url):
        mon_url = '/images?name=' + osname + '&version=' + osversion + '&isoweb=' + source_url
        serverip = self._get_serverip()
        control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
        response = fit_common.restful(
            "http://" +
            serverip +
            ":" + control_port +
            mon_url,
            rest_action="put",
            rest_payload={},
            rest_timeout=None,
            rest_headers={})
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201, got:' + str(response['status']))
            return "fail"

    def _list_file(self, mon_url):
        serverip = self._get_serverip()
        control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url)
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _delete_os_image(self, osname, osversion):
        mon_url = '/images?name=' + osname + '&version=' + osversion
        serverip = self._get_serverip()
        control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url, rest_action="delete")
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _delete_os_iso(self, isoname):
        mon_url = '/iso?name=' + isoname
        serverip = self._get_serverip()
        control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url, rest_action="delete")
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _wait_for_task_complete(self, taskid, retries=60):
        for dummy in range(0, retries):
            result = fit_common.rackhdapi('/api/2.0/workflows/' + taskid)
            if result['json']["status"] == 'running' or result['json']["status"] == 'pending':
                logs.debug("OS Install workflow state: {}".format(result['json']["status"]))
                fit_common.time.sleep(30)
            elif result['json']["status"] == 'succeeded':
                logs.debug("OS Install workflow state: {}".format(result['json']["status"]))
                return True
            else:
                break
        logs.error("Task failed with the following state: " + result['json']["status"])
        return False

    def _get_tester_ip(self):
        serverip = self._get_serverip()
        monip = fit_common.fitcfg()["rackhd-config"]["apiServerAddress"]
        cmd = "ping -R -c 1 " + monip + ""
        (command_output, exitstatus) = pexpect.run(
            "ssh -q -o StrictHostKeyChecking=no -t " + fit_common.fitcfg()["image_service"]['usr'] + "@" + serverip +
            " sudo bash -c \\\"" + cmd + "\\\"", withexitstatus=1,
            events={"assword": fit_common.fitcfg()["image_service"]['pwd'] + "\n"}, timeout=300)
        uud = command_output.split("\t")
        myip = uud[1].split("\r\n")[0]
        logs.debug('My IP address is: ' + myip)
        return myip

    def _create_esxi_repo(self):
        logs.debug("create a ESXi repo")
        for osrepo in fit_common.fitcfg()["image_service"]["os_image"]:
            if osrepo["osname"] == "ESXi" and osrepo["version"] == "6.0":
                os_name = osrepo["osname"]
                os_version = osrepo["version"]
                http_iso_url = osrepo["url"]
                self._upload_os_by_network(os_name, os_version, http_iso_url)
                logs.debug("create ESXi repo successfully")
                return
        logs.error("No ESXi source found in config")

    def _delete_all_images(self):
        os_image_list = self._list_file('/images')
        serverip = self._get_serverip()
        for image_repo in os_image_list:
            self.assertNotEqual(
                self._delete_os_image(image_repo["name"], image_repo["version"]), "fail", "delete image failed!")
            control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
            fileurlprefix = "http://" + serverip + ":" + control_port + "/" + \
                            image_repo["name"] + '/' + image_repo["version"] + '/'
            self.assertFalse(self._file_exists(fileurlprefix), "The repo url is not deleted completely")
        os_image_list_clear = self._list_file('/images')
        self.assertTrue(os_image_list_clear == [])
        os_iso_list = self._list_file('/iso')
        for iso_repo in os_iso_list:
            self.assertNotEqual(self._delete_os_iso(iso_repo["name"]), "fail", "delete iso failed!")
        os_iso_list_clear = self._list_file('/iso')
        self.assertTrue(os_iso_list_clear == [], "The iso is not deleted completely")
        logs.debug("All repo is cleared!")

    def _upload_microkernel(self, filename):
        myfile = open(filename, 'rb')
        serverip = self._get_serverip()
        mon_url = '/microkernel?name=' + filename
        control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url, rest_action="binary-put",
                                      rest_payload=myfile)
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.debug_3('Incorrect HTTP return code, expected 201, got:' + str(response['status']))
            return "fail"


    def _delete_microkernel(self, filename):
        mon_url = '/microkernel?name=' + filename
        serverip = self._get_serverip()
        control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url, rest_action="delete")
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.debug_3('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _scp_file(self, url):
        file_name = url.split('/')[-1]
        logs.debug_3("scp file %s from RackHD" % url)
        if not os.path.exists(file_name):
            path = url[6:]
            rackhd_hostname = fit_common.fitargs()['rackhd_host']
            scp_file = fit_common.fitcreds()['rackhd_host'][0]['username'] + '@{0}:{1}'.format(rackhd_hostname, path)
            cmd = 'scp -o StrictHostKeyChecking=no {0} .'.format(scp_file)
            logs.debug_3("scp command : '{0}'".format(cmd))
            logfile_redirect = None
            if fit_common.VERBOSITY >= 9:
                logfile_redirect = sys.stdout
            (command_output, ecode) = pexpect.run(
                cmd, withexitstatus=1,
                events={'(?i)assword: ': fit_common.fitcreds()['rackhd_host'][0]['password'] + '\n'},
                logfile=logfile_redirect)
            assert ecode == 0, 'failed "{0}" because {1}. Output={2}'.format(cmd, ecode, command_output)
        return file_name

    def _download_file(self, url):
        logs.debug_3("downloading url=%s" % url)
        file_name = url.split('/')[-1]
        if os.path.exists(file_name) is False:
            u = urllib2.urlopen(url)
            f = open(file_name, 'wb')
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            logs.debug_3("Downloading: %s Bytes: %s" % (file_name, file_size))
            file_size_dl = 0
            block_sz = 8192
            while True:
                file_buffer = u.read(block_sz)
                if not file_buffer:
                    break
                file_size_dl += len(file_buffer)
                f.write(file_buffer)
                # logs dose not have ability to draw digital in original place. use print instead.
                if fit_common.VERBOSITY >= 9:
                    status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                    status = status + chr(8) * (len(status) + 1) + "\r"
                    print(status)
            f.close()
        return file_name

    def _upload_all_microkernels(self):
        for microkernelrepo in fit_common.fitcfg()["image_service"]["microkernel"]:
            if microkernelrepo[:3] == "scp":
                file_name = self._scp_file(microkernelrepo)
            else:
                file_name = self._download_file(microkernelrepo)
            self._upload_microkernel(file_name)
            self._release(file_name)

    def _release(self, file_name):
        try:
            logs.debug_3("rm " + file_name)
            os.system("rm " + file_name)
            return True
        except OSError:
            return False

    def _delete_all_microkernels(self):
        microkernel_list = self._list_file('/microkernel')
        for microkernel in microkernel_list:
            self.assertNotEqual(self._delete_microkernel(microkernel["name"]), "fail", "delete image failed!")
        microkernel_list_clear = self._list_file('/microkernel')
        self.assertTrue(microkernel_list_clear == [])
        logs.debug_3("All microkernels are cleared!")

    def _delete_all_images(self):
        os_image_list = self._list_os_image()
        serverip = self._get_serverip()
        for image_repo in os_image_list:
            self.assertNotEqual(
                self._delete_os_image(image_repo["name"], image_repo["version"]), "fail", "delete image failed!")
            file_port = str(fit_common.fitcfg()["image_service"]["file_port"])
            fileurlprefix = "http://" + serverip + ":" + file_port + "/" + image_repo["name"] + '/' + \
                            image_repo["version"] + '/'
            self.assertFalse(self._file_exists(fileurlprefix), "The repo url does not deleted completely")
        os_image_list_clear = self._list_os_image()
        self.assertTrue(os_image_list_clear == [])
        os_iso_list = self._list_os_iso()
        for iso_repo in os_iso_list:
            self.assertNotEqual(self._delete_os_iso(iso_repo["name"]), "fail", "delete iso failed!")
        os_iso_list_clear = self._list_os_iso()
        self.assertTrue(os_iso_list_clear == [], "The iso does not deleted completely")
        logs.debug("All repo is cleared!")

    def _wait_for_discover(self, node_uuid):
        for dummy in range(0, 30):
            fit_common.time.sleep(30)
            rest_data = fit_common.rackhdapi('/redfish/v1/Systems/')
            if rest_data['json']['Members@odata.count'] == 0:
                continue
            node_collection = rest_data['json']['Members']
            for computenode in node_collection:
                nodeidurl = computenode['@odata.id']
                api_data = fit_common.rackhdapi(nodeidurl)
                if api_data['status'] > 399:
                    break
                if node_uuid == api_data['json']['UUID']:
                    return True
        logs.error("Timeout in rediscovery!")
        return False

    def test_bootstrapping_ext_esxi6(self):
        self._create_esxi_repo()
        node_collection = test_api_utils.get_node_list_by_type("compute")
        fileserver_ip = self._get_tester_ip()
        file_port = str(fit_common.fitcfg()["image_service"]["file_port"])
        repourl = "http://" + fileserver_ip + ':' + file_port + '/ESXi' + '/' + '6.0' + '/'
        # Select one node at random
        for dummy in node_collection:
            node = node_collection[random.randint(0, len(node_collection) - 1)]
        logs.debug('Running ESXI 6.0 bootstrap from external file server.')
        node_obm = fit_common.rackhdapi(
            '/api/2.0/nodes/' + node)['json']['obms']
        if node_obm == []:
            self.assertTrue(self._apply_obmsetting_to_node(node), "Fail to apply obm setting!")
        fit_common.rackhdapi(
            '/api/2.0/nodes/' + node + '/workflows/action', action='put',
            payload={
                "command": "cancel",
                "options": {}
            })
        nodehostname = 'esxi60'
        payload_data = {"options": {
                        "defaults": {
                            "version": "6.0",
                            "repo": repourl,
                            "rootPassword": "1234567",
                            "hostname": nodehostname
                        }}}
        result = fit_common.rackhdapi(
            '/api/2.0/nodes/' + node + '/workflows?name=Graph.InstallEsxi', action='post', payload=payload_data)
        self.assertEqual(
            result['status'], 201, 'Was expecting code 201. Got ' + str(result['status']))
        self.assertEqual(
            self._wait_for_task_complete(result['json']["instanceId"], retries=80), True,
            'TaskID ' + result['json']["instanceId"] + ' not successfully completed.')
        self._delete_all_images()

    def test_rediscover(self):
        # Select one node at random that's not a management server
        self._upload_all_microkernels()
        node_collection = test_api_utils.get_node_list_by_type("compute")
        for dummy in node_collection:
            node = node_collection[random.randint(0, len(node_collection) - 1)]
            if fit_common.rackhdapi('/api/2.0/nodes/' + node)['json']['name'] != "Management Server":
                break
        logs.debug_3('Checking OBM setting...')
        node_obm = fit_common.rackhdapi('/api/2.0/nodes/' + node)['json']['obms']
        if node_obm == []:
            self.assertTrue(self._apply_obmsetting_to_node(node), "Fail to apply obm setting!")
        node_uuid = fit_common.rackhdapi('/redfish/v1/Systems/' + node)['json']['UUID']
        logs.debug_3('UUID of selected Node is:' + node_uuid)
        # Cancel all active workflow on target node
        fit_common.rackhdapi(
            '/api/2.0/nodes/' + node + '/workflows/action', action='put',
            payload={
                "command": "cancel",
                "options": {}
            })
        logs.debug_3('Running rediscover, resetting system node...')
        # Reboot the node to begin rediscover.
        resetresponse = fit_common.rackhdapi(
            '/redfish/v1/Systems/' + node + '/Actions/ComputerSystem.Reset', action='post',
            payload={"reset_type": "ForceRestart"})
        self.assertTrue(resetresponse['status'] < 209,
                        'Incorrect HTTP return code, expected <209 , got:' + str(resetresponse['status']))
        # Delete original node
        for dummy in range(0, 30):
            time.sleep(2)
            result = fit_common.rackhdapi('/api/2.0/nodes/' + node, action='delete')
            if result['status'] < 209:
                break
        self.assertTrue(result['status'] < 209, 'Was expecting response code < 209. Got ' + str(result['status']))
        logs.debug_3("Waiting node reboot and boot into microkernel........")
        self.assertTrue(self._wait_for_discover(node_uuid), "Fail to find the orignial node after reboot!")
        logs.debug_3("Found the orignial node. It is rediscovered succesfully!")
        self._delete_all_microkernels()


if __name__ == '__main__':
    unittest.main()
