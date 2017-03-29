'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

Author(s):
Norton Luo
his test validate the image-service of RackHD. It stores the micorkernel image used for node discovery.
This test focus on image service microkernel related functionality itself.
'''

import os
import sys
import urllib2
import requests
import flogging
import pexpect
import fit_common
import unittest
from nose.plugins.attrib import attr
logs = flogging.get_loggers()
control_port = str(fit_common.fitcfg()["image_service"]["control_port"])
file_port = str(fit_common.fitcfg()["image_service"]["file_port"])
test_microkernel_urls = fit_common.fitcfg()["image_service"]["microkernel"]


@attr(all=True, regression=False, smoke=False)
class static_microkernel_image_service(fit_common.unittest.TestCase):
    def setUp(self):
        self.test_delete_microkernels()

    def tearDown(self):
        self.test_delete_microkernels()

    def _get_serverip(self):
        args = fit_common.fitargs()['unhandled_arguments']
        for arg in args:
            if "imageserver" in arg:
                serverip = arg.split("=")[1]
                return serverip
        return fit_common.fitcfg()["image_service"]["imageserver"]

    def _release(self, file_name):
        try:
            logs.debug_3("rm " + file_name)
            os.system("rm " + file_name)
            return True
        except OSError:
            return False

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
                    print status
            f.close()
        return file_name

    def _file_exists(self, location):
        state = requests.head(location).status_code
        logs.debug_3("restful: Status code =%s" % state)
        if int(state) < 400:
            return True
        else:
            return False

    def _upload_microkernel(self, filename):
        myfile = open(filename, 'rb')
        serverip = self._get_serverip()
        mon_url = '/microkernel?name=' + filename
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url, rest_action="binary-put",
                                      rest_payload=myfile)
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.debug_3('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _list_microkernel(self):
        mon_url = '/microkernel'
        serverip = self._get_serverip()
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url)
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.debug_3('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _delete_microkernel(self, filename):
        mon_url = '/microkernel?name=' + filename
        serverip = self._get_serverip()
        response = fit_common.restful("http://" + serverip + ":" + control_port + mon_url, rest_action="delete")
        if response['status'] in range(200, 205):
            return response['json']
        else:
            logs.debug_3('Incorrect HTTP return code, expected 201-205, got:' + str(response['status']))
            return "fail"

    def _scp_file(self, url):
        file_name = url.split('/')[-1]
        logs.debug_3("scp file %s from RackHD" % url)
        if os.path.exists(file_name) is False:
            path = url[6:]
            rackhd_hostname = fit_common.fitargs()['rackhd_host']
            scp_file = fit_common.fitcreds()['rackhd_host'][0]['username'] + '@{0}:{1}'.format(rackhd_hostname, path)
            cmd = 'scp -o StrictHostKeyChecking=no {0} .'.format(scp_file)
            logs.debug_3("scp command : '{0}'".format(cmd))
            if fit_common.VERBOSITY >= 9:
                logfile_redirect = sys.stdout
            (command_output, ecode) = pexpect.run(
                cmd, withexitstatus=1,
                events={'(?i)assword: ': fit_common.fitcreds()['rackhd_host'][0]['password'] + '\n'},
                logfile=logfile_redirect)
            assert ecode == 0, 'failed "{0}" because {1}. Output={2}'.format(cmd, ecode, command_output)
        return file_name

    def test_upload_list_microkernel(self):
        microkernel_list = []
        serverip = self._get_serverip()
        for microkernelrepo in test_microkernel_urls:
            if microkernelrepo[:3] == "scp":
                file_name = self._scp_file(microkernelrepo)
            else:
                file_name = self._download_file(microkernelrepo)
            self.assertNotEqual(self._upload_microkernel(file_name), "fail", "Upload microkernel failed!")
            microkernel_list.append(file_name)
            fileurl = "http://" + serverip + ":" + file_port + "/common/" + file_name
            self.assertTrue(self._file_exists(fileurl), "The microkernel file url could not found!")
            logs.debug_3("microkernel_list=%s" % microkernel_list)
            self._release(file_name)
        # time.sleep(60)
        micorkernel_json_list = self._list_microkernel()
        for kernelurl in microkernel_list:
            found_flag = False
            for microkernel in micorkernel_json_list:
                if microkernel["name"] == kernelurl:
                    found_flag = True
                    break
            self.assertTrue(found_flag, "microkernel with name: " + kernelurl + " not found!")
            logs.debug_3("Found all microkernels, list is correct!")

    def test_delete_microkernels(self):
        microkernel_list = self._list_microkernel()
        serverip = self._get_serverip()
        for microkernel in microkernel_list:
            self.assertNotEqual(self._delete_microkernel(microkernel["name"]), "fail", "delete image failed!")
            fileurl = "http://" + serverip + ":" + file_port + "/common/" + microkernel["name"]
            self.assertFalse(self._file_exists(fileurl), "The kernel image does not deleted completely")
        microkernel_list_clear = self._list_microkernel()
        self.assertTrue(microkernel_list_clear == [])
        logs.debug_3("All microkernels are cleared!")


if __name__ == '__main__':
    unittest.main()
