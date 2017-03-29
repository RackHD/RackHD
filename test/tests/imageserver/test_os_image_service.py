'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo
This test validate the image-service of RackHD. It use OS iso file stored in remote server server to load on
the image-service server. This test will create os repo in the server and then go through the repo directories and
compare files&directories with the local iso image. This test focus on image service OS repo functionality itself.
You need put an config file in the /config directory
'''

import os
import urllib2
import flogging
import requests
import fit_common
import pexpect
import unittest
import test_api_utils
from nose.plugins.attrib import attr
logs = flogging.get_loggers()
control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
file_port = str(fit_common.fitcfg()["image_service"]["file_port"])


@attr(all=True, regression=False, smoke=False)
class test_os_image_service(fit_common.unittest.TestCase):
    def setUp(self):
        self.test_delete_all_images()

    def _get_serverip(self):
        args = fit_common.fitargs()['unhandled_arguments']
        for arg in args:
            if "imageserver" in arg:
                serverip = arg.split("=")[1]
                return serverip
        return fit_common.fitcfg()["image_service"]["imageserver"]

    def _mount_local_os_repo(self, file_name, mountpoint):
        try:
            if os.path.exists(mountpoint) is False:
                command = "mkdir " + mountpoint
                os.popen(command)
            # use fuseiso tool to mount without root privilege. user need install fuseiso before the test.
            command = "fuseiso " + file_name + " " + mountpoint
            os.popen(command)
            return True
        except OSError:
            return False

    def _apply_obmsetting_to_node(self, nodeid):
        usr = ''
        pwd = ''
        response = fit_common.rackhdapi(
            '/api/2.0/nodes/' + nodeid + '/catalogs/bmc')
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

    def _release(self, file_name, mountpoint):
        try:
            # use fusermount to umount the iso loaded by fuseiso without root privilege. User need intall it first.
            logs.debug("fusermount -u" + mountpoint)
            os.system("fusermount -u " + mountpoint)
            logs.debug("rm -d " + mountpoint)
            os.system("rm -d " + mountpoint)
            logs.debug("rm " + file_name)
            os.system("rm " + file_name)
            return True
        except OSError:
            return False

    def _download_file(self, url):
        logs.debug_3("downloading url= %s" % url)
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
                buffer = u.read(block_sz)
                if not buffer:
                    break
                file_size_dl += len(buffer)
                f.write(buffer)
                # logs dose not have ability to draw digital in original place. use print instead.
                if fit_common.VERBOSITY >= 9:
                    status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
                    status = status + chr(8) * (len(status) + 1) + "\r"
                    print status
            f.close()
        return file_name

    def _file_exists(self, location):
        # check file header only to save time.
        state = requests.head(location).status_code
        logs.debug_3("restful: Status code = %s" % state)
        if int(state) < 400:
            return True
        else:
            return False

    def _compare_repo(self, walkpath, os_version):
        # Go through all the files in the repo.
        # To save time, filetocompare parameter is provide in config file to set max file number to go through.
        logs.debug_3("entering ..." + walkpath)
        os_name = walkpath
        serverip = self._get_serverip()
        fileurlprefix = "http://" + serverip + ":" + file_port + "/" + os_name + '/' + os_version
        filetocompare = fit_common.fitcfg()["image_service"]["filetocompare"]
        i = 0
        for path, dirs, files in os.walk("./" + walkpath):
            logs.debug_3(path)
            for f in files:
                logs.debug_3(f)
                a = path[2:]
                b = a.replace(walkpath, '', 1)
                fileurl = fileurlprefix + b + '/' + f
                logs.debug_3(fileurl)
                i = i + 1
                if i > filetocompare:
                    break
                if self._file_exists(fileurl) is False:
                    logs.error("File not found:" + "/" + path[2:] + "/" + f)
                    return False
        return True

    def _upload_iso_file(self, osname, osversion, filename):
        serverip = self._get_serverip()
        mon_url = '/images?name=' + osname + '&version=' + osversion + '&isoclient=' + filename
        myfile = open(filename, 'rb')
        response = fit_common.restful(
            "http://" + serverip + ":" + control_port + mon_url, rest_action="binary-put", rest_payload=myfile,
            rest_timeout=None, rest_headers={})
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _upload_iso_file_to_store(self, filename):
        serverip = self._get_serverip()
        mon_url = '/iso?name=' + filename
        file = open(filename, 'rb')
        response = fit_common.restful(
            "http://" + serverip + ":" + control_port + mon_url,
            rest_action="binary-put",
            rest_payload=file,
            rest_timeout=None,
            rest_headers={})
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _upload_os_by_network(self, osname, osversion, source_url):
        mon_url = '/images?name=' + osname + '&version=' + osversion + '&isoweb=' + source_url
        serverip = self._get_serverip()
        response = fit_common.restful(
            "http://" + serverip + ":" + control_port + mon_url,
            rest_action="put",
            rest_payload={},
            rest_timeout=None,
            rest_headers={})
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _upload_os_by_store(self, osname, osversion, filename):
        mon_url = '/images?name=' + osname + '&version=' + osversion + '&isostore=' + filename
        serverip = self._get_serverip()
        response = fit_common.restful(
            "http://" + serverip + ":" + control_port + mon_url, rest_action="put", rest_payload={}, rest_timeout=None,
            rest_headers={})
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _upload_os_from_local(self, osname, osversion, path):
        mon_url = '/images?name=' + osname + '&version=' + osversion + '&isolocal=' + path
        serverip = self._get_serverip()
        response = fit_common.restful(
            "http://" + serverip + ":" + control_port + mon_url, rest_action="put", rest_payload={}, rest_timeout=None,
            rest_headers={})
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _list_os_image(self):
        mon_url = '/images'
        serverip = self._get_serverip()
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url)
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _list_os_iso(self):
        mon_url = '/iso'
        serverip = self._get_serverip()
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url)
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _delete_os_image(self, osname, osversion):
        mon_url = '/images?name=' + osname + '&version=' + osversion
        serverip = self._get_serverip()
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url, rest_action="delete")
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.error('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _delete_os_iso(self, isoname):
        mon_url = '/iso?name=' + isoname
        serverip = self._get_serverip()
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

    def test_create_os_repo_from_iso_upload(self):
        for osrepo in fit_common.fitcfg()["image_service"]["os_image"]:
            file_name = self._download_file(osrepo["url"])
            self.assertNotEqual(
                self._upload_iso_file(osrepo["osname"], osrepo["version"], file_name), "fail", "upload image failed!")
            self.assertTrue(self._mount_local_os_repo(file_name, osrepo["osname"]), "Could not mount ISO")
            self.assertTrue(self._compare_repo(osrepo["osname"], osrepo["version"]), "Fileserver compare failed!")
            self._release(file_name, osrepo["osname"])
        self.test_delete_all_images()

    def test_create_os_repo_from_http(self):
        for osrepo in fit_common.fitcfg()["image_service"]["os_image"]:
            if osrepo["linktype"] == "http":
                os_name = osrepo["osname"]
                os_version = osrepo["version"]
                http_iso_url = osrepo["url"]
                self.assertNotEqual(
                    self._upload_os_by_network(os_name, os_version, http_iso_url), "fail", "upload image failed!")
                file_name = self._download_file(http_iso_url)
                self.assertTrue(self._mount_local_os_repo(file_name, os_name), "Could not mount ISO")
                self.assertTrue(self._compare_repo(os_name, os_version), "Fileserver compare failed!")
                self._release(file_name, os_name)
        self.test_delete_all_images()

    def test_create_os_repo_from_ftp(self):
        for osrepo in fit_common.fitcfg()["image_service"]["os_image"]:
            if osrepo["linktype"] == "ftp":
                os_name = osrepo["osname"]
                os_version = osrepo["version"]
                ftp_iso_url = osrepo["url"]
                self.assertNotEqual(
                    self._upload_os_by_network(os_name, os_version, ftp_iso_url), "fail", "upload image failed!")
                file_name = self._download_file(ftp_iso_url)
                self.assertTrue(self._mount_local_os_repo(file_name, os_name), "Could not mount ISO")
                self.assertTrue(self._compare_repo(os_name, os_version), "Fileserver compare failed!")
                self._release(file_name, os_name)
        self.test_delete_all_images()

    def test_create_os_repo_from_store(self):
        for osrepo in fit_common.fitcfg()["image_service"]["os_image"]:
            os_name = osrepo["osname"]
            os_version = osrepo["version"]
            iso_url = osrepo["url"]
            file_name = self._download_file(iso_url)
            self.assertNotEqual(self._upload_iso_file_to_store(file_name), "fail", "upload image failed!")
            self.assertNotEqual(
                self._upload_os_by_store(os_name, os_version, file_name), "fail", "upload image failed!")
            self.assertTrue(self._mount_local_os_repo(file_name, os_name), "Could not mount ISO")
            self.assertTrue(self._compare_repo(os_name, os_version), "Fileserver compare failed!")
            self._release(file_name, os_name)
        self.test_delete_all_images()

    def test_create_os_repo_from_local(self):
        for osrepo in fit_common.fitcfg()["image_service"]["os_image"]:
            os_name = osrepo["osname"]
            os_version = osrepo["version"]
            iso_url = osrepo["url"]
            servercmd = "wget " + osrepo["url"]
            serverip = self._get_serverip()
            fit_common.remote_shell(
                shell_cmd=servercmd, address=serverip, user=fit_common.fitcfg()["image_service"]['usr'],
                password=fit_common.fitcfg()["image_service"]['pwd'])
            path = "/home/" + fit_common.fitcfg()["image_service"]['usr']
            file_name = self._download_file(iso_url)
            self.assertNotEqual(
                self._upload_os_from_local(os_name, os_version, path + '/' + file_name), "fail", "upload image failed!")
            self.assertTrue(self._mount_local_os_repo(file_name, os_name), "Could not mount ISO")
            self.assertTrue(self._compare_repo(os_name, os_version), "Fileserver compare failed!")
            self._release(file_name, os_name)
        self.test_delete_all_images()

    def test_list_images(self):
        os_id_list = []
        for osrepo in fit_common.fitcfg()["image_service"]["os_image"]:
            os_name = osrepo["osname"]
            os_version = osrepo["version"]
            response = self._upload_os_by_network(os_name, os_version, osrepo["url"])
            self.assertNotEqual(response, "fail", "upload iso failed!")
            id = response["id"]
            os_id_list.append(id)
            logs.debug("os_id_list=", os_id_list)
        os_image_list = self._list_os_image()
        for osid in os_id_list:
            found_flag = False
            for image_repo in os_image_list:
                if image_repo["id"] == osid:
                    found_flag = True
                    break
            self.assertTrue(found_flag, "image with id " + osid + " not found!")
        logs.error("Found all os, list is correct!")

    def test_delete_all_images(self):
        os_image_list = self._list_os_image()
        serverip = self._get_serverip()
        for image_repo in os_image_list:
            self.assertNotEqual(
                self._delete_os_image(image_repo["name"], image_repo["version"]), "fail", "delete image failed!")
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


if __name__ == '__main__':
    unittest.main()
