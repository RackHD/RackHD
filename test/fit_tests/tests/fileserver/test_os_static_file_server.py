'''
Copyright 2016, DELL|EMC, Inc.

Author(s):
Norton Luo

'''

import os
import sys
import subprocess
import urllib2
import string
import time
import requests
import random
import json
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common

try:
    FILE_CONFIG = json.loads(open(fit_common.CONFIG_PATH + "fileserver_config.json").read())
except:
    print "**** Global Config file: " + fit_common.CONFIG_PATH + "FILE_CONFIG.json" + " missing or corrupted! Exiting...."
    sys.exit(255)
filetocompare=100



def filerestful(url_command, rest_action='get', rest_payload=[], rest_timeout=None, sslverify=False, rest_headers={}):
    '''
    This function is a copy of the restful function used in fit_common. Due to the external file server used different authtication.
    This routine executes a rest API call to the host.

    :param url_command: the full URL for the command
    :param rest_action: what the restful do (get/post/put/delete)
    :param rest_payload: payload for rest request
    :param rest_headers: headers (JSON dict)
    :param rest_timeout: timeout for rest request
    :param sslverify: ssl Verify (True/False)
    :return:    {'json':result_data.json(), 'text':result_data.text,
                'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}
    '''
    result_data = None
    # print URL and action
    if fit_common.VERBOSITY >= 4:
        print "restful: Action = ", rest_action, ", URL = ", url_command
    # prepare payload for XML output
    payload_print = []
    try:
        json.dumps(rest_payload)
    except:
        payload_print = []
    else:
        payload_print = json.dumps(rest_payload, sort_keys=True, indent=4,)
        if len(payload_print) > 4096:
            payload_print = payload_print[0:4096] + '\n...truncated...\n'
        if fit_common.VERBOSITY >= 7 and rest_payload != []:
            print "restful: Payload =\n", payload_print

    rest_headers.update({"Content-Type": "application/json"})
    if fit_common.VERBOSITY >= 5:
         print "restful: Request Headers =", rest_headers, "\n"

    # If AUTH_TOKEN is set, add to header
    #if AUTH_TOKEN != "None" and AUTH_TOKEN != "Unavailable" and "authorization" not in rest_headers:
    #    rest_headers.update({"authorization": "JWT " + AUTH_TOKEN, "X-Auth-Token": REDFISH_TOKEN})
    # Perform rest request
    try:
        if rest_action == "get":
            result_data = requests.get(url_command,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       headers=rest_headers)
        if rest_action == "delete":
            result_data = requests.delete(url_command,
                                          data=json.dumps(rest_payload),
                                          timeout=rest_timeout,
                                          verify=sslverify,
                                          headers=rest_headers)
        if rest_action == "put":
            result_data = requests.put(url_command,
                                       data=json.dumps(rest_payload),
                                       headers=rest_headers,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       )
        if rest_action == "binary-put":
            rest_headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            result_data = requests.put(url_command,
                                       data=rest_payload,
                                       headers=rest_headers,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       )
        if rest_action == "text-put":
            rest_headers.update({"Content-Type": "text/plain"})
            result_data = requests.put(url_command,
                                       data=rest_payload,
                                       headers=rest_headers,
                                       timeout=rest_timeout,
                                       verify=sslverify,
                                       )
        if rest_action == "post":
            result_data = requests.post(url_command,
                                        data=json.dumps(rest_payload),
                                        headers=rest_headers,
                                        timeout=rest_timeout,
                                        verify=sslverify
                                        )
        if rest_action == "binary-post":
            rest_headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            result_data = requests.post(url_command,
                                        data=rest_payload,
                                        headers=rest_headers,
                                        timeout=rest_timeout,
                                        verify=sslverify
                                        )
        if rest_action == "text-post":
            rest_headers.update({"Content-Type": "text/plain"})
            result_data = requests.post(url_command,
                                        data=rest_payload,
                                        headers=rest_headers,
                                        timeout=rest_timeout,
                                        verify=sslverify
                                        )
        if rest_action == "patch":
            result_data = requests.patch(url_command,
                                         data=json.dumps(rest_payload),
                                         headers=rest_headers,
                                         timeout=rest_timeout,
                                         verify=sslverify
                                         )
    except requests.exceptions.Timeout:
        return {'json':'', 'text':'',
                'status':0,
                'headers':'',
                'timeout':True}

    try:
        result_data.json()
    except ValueError:

        if fit_common.VERBOSITY >= 9:
            print "restful: TEXT =\n"
            print result_data.text
        if fit_common.VERBOSITY >= 6:
            print "restful: Response Headers =", result_data.headers, "\n"
        if fit_common.VERBOSITY >= 4:
            print "restful: Status code =", result_data.status_code, "\n"
        return {'json':{}, 'text':result_data.text, 'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}
    else:

        if fit_common.VERBOSITY >= 9:
            print "restful: JSON = \n"
            print json.dumps(result_data.json(), sort_keys=True, indent=4)
        if fit_common.VERBOSITY >= 6:
            print "restful: Response Headers =", result_data.headers, "\n"
        if fit_common.VERBOSITY >= 4:
            print "restful: Status code =", result_data.status_code, "\n"
        return {'json':result_data.json(), 'text':result_data.text,
                'status':result_data.status_code,
                'headers':result_data.headers,
                'timeout':False}


def mount_local_os_repo(file_name,mountpoint):
    try:
        if os.path.exists(mountpoint)==False:
            os.system("sudo mkdir "+mountpoint)
        os.system("sudo mount -o rw,loop "+file_name+" "+mountpoint)
        return True
    except OSError:
        return False

def release(file_name,mountpoint):
    try:
        print "sudo umount "+mountpoint
        os.system("sudo umount "+mountpoint)
        print "sudo rm -d "+mountpoint
        os.system("sudo rm -d "+mountpoint)
        print "sudo rm "+file_name
        os.system("sudo rm "+file_name)
        return True
    except OSError:
        return False


def download_file(url):
    print "downloading url=",url
    file_name = url.split('/')[-1]
    if os.path.exists(file_name)==False :
        u = urllib2.urlopen(url)
        f = open(file_name, 'wb')
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (file_name, file_size)
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print status,
        f.close()
    return file_name


def file_exists(location):
    state=requests.head(location).status_code
    if fit_common.VERBOSITY >= 4:
        print "restful: Status code =", state
    if int(state)<400:
        return True
    else:
        return False


def compare_repo(walkpath,os_version):
    print "entering ..."+walkpath
    os_name=walkpath
    serverip=os.getenv("IMAGESERVER", "localhost")
    fileurlprefix="http://"+serverip+":9090/"+os_name+'/'+os_version
    i=0
    for path, dirs, files in os.walk("./"+walkpath):
        print path
        for f in files:
            print f
            a=path[2:]
            b=a.replace(walkpath,'',1)
            fileurl=fileurlprefix+b+'/'+f
            print fileurl
            i=i+1
            if i>filetocompare:
                break
            if file_exists(fileurl)==False:
                print "File not found:"+"/"+ path[2:]+"/"+f
                return False
    return True


def upload_iso_file(osname,osversion,filename):

    serverip=os.getenv("IMAGESERVER", "localhost")
    mon_url = '/images?name='+osname+'&version='+osversion+'&isoclient='+filename
    file = open(filename, 'rb')
    response =filerestful( "http://" + serverip + ":7070" + mon_url,rest_action="binary-put", rest_payload=file, rest_timeout=None, rest_headers={})


    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"


def upload_iso_file_to_store(filename):

    serverip=os.getenv("IMAGESERVER", "localhost")
    mon_url = '/iso?name='+ filename
    file = open(filename, 'rb')
    response =filerestful( "http://" + serverip + ":7070" + mon_url,rest_action="binary-put", rest_payload=file, rest_timeout=None, rest_headers={})
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"


def upload_os_by_network(osname,osversion,source_url):
    mon_url = '/images?name='+osname+'&version='+osversion+'&isoweb='+source_url
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url,rest_action="put", rest_payload={}, rest_timeout=None, rest_headers={})

    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"

def upload_os_by_store(osname,osversion,filename):
    mon_url = '/images?name='+osname+'&version='+osversion+'&isostore='+filename
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url,rest_action="put", rest_payload={}, rest_timeout=None, rest_headers={})
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"

def upload_os_from_local(osname,osversion,path):
    mon_url = '/images?name='+osname+'&version='+osversion+'&isolocal='+path
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url,rest_action="put", rest_payload={}, rest_timeout=None, rest_headers={})
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"


def list_os_image():
    mon_url = '/images'
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url)
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"

def list_os_iso():
    mon_url = '/iso'
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url)
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"



def delete_os_image(osname,osversion):
    mon_url = '/images?name='+osname+'&version='+osversion
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url,rest_action="delete")
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"


def delete_os_iso(isoname):
    mon_url = '/iso?name='+isoname
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url,rest_action="delete")
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"

# this routine polls a task ID for completion
def wait_for_task_complete(taskid, retries=60):
    for dummy in range(0, retries):
        result = fit_common.rackhdapi('/api/2.0/workflows/'+taskid)
        if result['json']["status"] == 'running' or result['json']["status"] == 'pending':
            if fit_common.VERBOSITY >= 2:
                print "OS Install workflow state: {}".format(result['json']["status"])
            fit_common.time.sleep(30)
        elif result['json']["status"] == 'succeeded':
            if fit_common.VERBOSITY >= 2:
                print "OS Install workflow state: {}".format(result['json']["status"])
            return True
        else:
            break
    print "Task failed with the following state: " + result['json']["status"]
    return False


# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=False, smoke=False)
class static_os_file_server(fit_common.unittest.TestCase):
    def test_create_os_repo_from_iso_upload(self):
        for osrepo in FILE_CONFIG["os_image"]:
            file_name=download_file(osrepo["url"])
            self.assertNotEqual(upload_iso_file(osrepo["osname"],osrepo["version"],file_name),"fail","upload image failed!")
            self.assertTrue(mount_local_os_repo(file_name,osrepo["osname"]),"Could not mount ISO")
            self.assertTrue(compare_repo(osrepo["osname"],osrepo["version"]),"Fileserver compare failed!")
            release(file_name,osrepo["osname"])


    def test_create_os_repo_from_http(self):
        for osrepo in FILE_CONFIG["os_image"]:
            if osrepo["linktype"]=="http":
                os_name=osrepo["osname"]
                os_version=osrepo["version"]
                http_iso_url=osrepo["url"]
                self.assertNotEqual(upload_os_by_network(os_name,os_version,http_iso_url),"fail","upload image failed!")
                file_name=download_file(http_iso_url)
                self.assertTrue(mount_local_os_repo(file_name,os_name),"Could not mount ISO")
                self.assertTrue(compare_repo(os_name,os_version),"Fileserver compare failed!")
                release(file_name,os_name)

    def test_create_os_repo_from_ftp(self):
        for osrepo in FILE_CONFIG["os_image"]:
            if osrepo["linktype"]=="ftp":
                os_name=osrepo["osname"]
                os_version=osrepo["version"]
                ftp_iso_url=osrepo["url"]
                self.assertNotEqual(upload_os_by_network(os_name,os_version,ftp_iso_url),"fail","upload image failed!")
                file_name=download_file(ftp_iso_url)
                self.assertTrue(mount_local_os_repo(file_name,os_name),"Could not mount ISO")
                self.assertTrue(compare_repo(os_name,os_version),"Fileserver compare failed!")
                release(file_name,os_name)

    def test_create_os_repo_from_store(self):
        for osrepo in FILE_CONFIG["os_image"]:
            os_name=osrepo["osname"]
            os_version=osrepo["version"]
            iso_url=osrepo["url"]
            file_name=download_file(iso_url)
            self.assertNotEqual(upload_iso_file_to_store(file_name),"fail","upload image failed!")
            self.assertNotEqual(upload_os_by_store(os_name,os_version,file_name),"fail","upload image failed!")
            self.assertTrue(mount_local_os_repo(file_name,os_name),"Could not mount ISO")
            self.assertTrue(compare_repo(os_name,os_version),"Fileserver compare failed!")
            release(file_name,os_name)

    def test_create_os_repo_from_local(self):
        for osrepo in FILE_CONFIG["os_image"]:
            os_name=osrepo["osname"]
            os_version=osrepo["version"]
            iso_url=osrepo["url"]
            servercmd="wget "+osrepo["url"]
            serverip=os.getenv("IMAGESERVER", "localhost")
            fit_common.remote_shell(shell_cmd=servercmd, address=serverip, user=FILE_CONFIG['usr'], password=FILE_CONFIG['pwd'])
            path="/home/"+FILE_CONFIG['usr']
            file_name=download_file(iso_url)
            self.assertNotEqual(upload_os_from_local(os_name,os_version,path+'/'+file_name),"fail","upload image failed!")
            self.assertTrue(mount_local_os_repo(file_name,os_name),"Could not mount ISO")
            self.assertTrue(compare_repo(os_name,os_version),"Fileserver compare failed!")
            release(file_name,os_name)

    def test_list_images(self):
        os_id_list=[]
        for osrepo in FILE_CONFIG["os_image"]:
            os_name=osrepo["osname"]
            os_version=osrepo["version"]
            response=upload_os_by_network(os_name,os_version,osrepo["url"])
            self.assertNotEqual(response,"fail","upload iso failed!")
            id=response["id"]
            os_id_list.append(id)
            print "os_id_list=",os_id_list
        os_image_list=list_os_image()
        for osid in os_id_list:
            found_flag=False
            for image_repo in os_image_list:
                if image_repo["id"]==osid:
                    found_flag=True
                    break
            self.assertTrue(found_flag,"image with id "+osid+" not found!")
        print "Found all os, list is correct!"

    def test_delete_all_images(self):
        os_image_list=list_os_image()
        serverip=os.getenv("IMAGESERVER", "localhost")
        for image_repo in os_image_list:
            self.assertNotEqual(delete_os_image(image_repo["name"],image_repo["version"]),"fail","delete image failed!")
            fileurlprefix="http://"+serverip+":9090/"+image_repo["name"]+'/'+image_repo["version"]+'/'
            self.assertFalse(file_exists(fileurlprefix),"The repo url does not deleted completely")
        os_image_list_clear=list_os_image()
        self.assertTrue(os_image_list_clear==[])
        os_iso_list=list_os_iso()
        for iso_repo in os_iso_list:
            self.assertNotEqual(delete_os_iso(iso_repo["name"]),"fail","delete iso failed!")
        os_iso_list_clear=list_os_iso()
        self.assertTrue(os_iso_list_clear==[],"The iso does not deleted completely")
        print "All repo is cleared!"

    def test_bootstrapping_ext_esxi6(self):
        NODECATALOG = fit_common.node_select()
        NODE = ""
        serverip=os.getenv("FILESERVER", "localhost")
        repourl= "http://"+serverip+':9090/'+'esxi'+'/'+'6.0'+'/'
        # Select one node at random that's not a management server
        for dummy in NODECATALOG:
            NODE = NODECATALOG[random.randint(0, len(NODECATALOG)-1)]
            if fit_common.rackhdapi('/api/2.0/nodes/' + NODE)['json']['name'] != "Management Server":
                break
        if fit_common.VERBOSITY >= 2:
            print 'Running ESXI 6.0 bootstrap from external file server.'
        fit_common.rackhdapi('/api/2.0/nodes/' + NODE + '/workflows/active', action='delete')
        nodehostname = 'esxi60'
        payload_data ={"options":{
                        "defaults":{
                        "version": "6.0",
                        "repo": repourl,
                        "rootPassword": "1234567",
                        "hostname": nodehostname,
                        "domain": "hwimo.lab.emc.com",
                        "dnsServers": ["172.31.128.1"],
                        "users": [{
                                    "name": "onrack",
                                    "password": "Onr@ck1!",
                                    "uid": 1010,
                                }]
                       }}}
        result = fit_common.rackhdapi('/api/2.0/nodes/'
                                            + NODE
                                            + '/workflows?name=Graph.InstallEsxi',
                                            action='post', payload=payload_data)
        self.assertEqual(result['status'], 201,
                         'Was expecting code 201. Got ' + str(result['status']))
        self.assertEqual(wait_for_task_complete(result['json']["instanceId"], retries=80), True,
                         'TaskID ' + result['json']["instanceId"] + ' not successfully completed.')

if __name__ == '__main__':
    fit_common.unittest.main()