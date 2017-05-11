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
import json
import requests
import random
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common


try:
    MICROKERNEL_CONFIG = json.loads(open(fit_common.CONFIG_PATH + "fileserver_config.json").read())
except:
    print "**** Global Config file: " + fit_common.CONFIG_PATH + "fileserver_config.json" + " missing or corrupted! Exiting...."
    sys.exit(255)
test_microkernel_url=MICROKERNEL_CONFIG["microkernel"]

# Local methods
NODECATALOG = fit_common.node_select()



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
        os.system("mkdir "+mountpoint)
        os.system("mount -o rw,loop "+file_name+" "+mountpoint)
        return True
    except OSError:
        return False

def release(file_name,mountpoint):
    try:
        print "rm -d"+mountpoint
        os.system("rm -d"+mountpoint)
        print "rm "+file_name
        os.system("rm "+file_name)
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

def upload_microkernel(filename):
    file = open(filename, 'rb')
    serverip=os.getenv("IMAGESERVER", "localhost")
    mon_url = '/microkernel?name='+filename
    response =filerestful( "http://" + serverip + ":7070" + mon_url,rest_action="binary-put", rest_payload=file)
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"

def list_microkernel():
    mon_url = '/microkernel'
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url)
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"

def delete_microkernel(filename):
    mon_url = '/microkernel?name='+filename
    serverip=os.getenv("IMAGESERVER", "localhost")
    response =filerestful( "http://" +serverip + ":7070" + mon_url,rest_action="delete")
    if response['status'] in range(200,205):
         return response['json']
    else:
         print 'Incorrect HTTP return code, expected 201, got:' + str(response['status'])
         return "fail"

# Check if the node is rediscovered. Retry in every 30 seconds and total 600 seconds.
def wait_for_discover(node_uuid):
    for dummy in range(0, 20):
        fit_common.time.sleep(30)
        rest_data=fit_common.rackhdapi('/redfish/v1/Systems/')
        if rest_data['json']['Members@odata.count']==0:
            continue
        node_collection= rest_data['json']['Members']
        for computenode in node_collection:
            nodeidurl=computenode['@odata.id']
            api_data=fit_common.rackhdapi(nodeidurl)
            if api_data['status']>399:
                break
            if node_uuid== api_data['json']['UUID']:
                return True
    print "Timeout!"
    return False

def apply_obmsetting(nodeid):
    usr=''
    pwd=''
    response= fit_common.rackhdapi('/api/2.0/nodes/'+nodeid+'/catalogs/bmc')
    bmcip= response['json']['data']['IP Address']
    #Try credential record in config file
    for creds in fit_common.GLOBAL_CONFIG['credentials']['bmc']:
        if fit_common.remote_shell('ipmitool -I lanplus -H ' + bmcip+' -U ' + creds['username']+' -P '+ creds['password'] + ' fru')['exitcode'] == 0:
            usr = creds['username']
            pwd = creds['password']
            break
    # Put the credential to OBM settings
    if  usr!="":
        payload = { "service": "ipmi-obm-service","config": {"host": bmcip, "user": usr,"password": pwd},"nodeId": nodeid}
        api_data = fit_common.rackhdapi("/api/2.0/obms", action='put', payload=payload)
        if api_data['status']== 201:
            return True
    return False


# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=False, smoke=False)
class static_microkernel_file_server(fit_common.unittest.TestCase):
    def setUp(self):
        self.test_delete_microkernels()


    def tearDown(self):
        self.test_delete_microkernels()

    def test_upload_list_microkernel(self):
        microkernel_list=[]
        serverip=os.getenv("IMAGESERVER", "localhost")
        for microkernelrepo in test_microkernel_url:
            file_name=download_file(microkernelrepo)
            self.assertNotEqual(upload_microkernel(file_name),"fail","Upload microkernel failed!")
            microkernel_list.append(file_name)
            fileurl="http://"+serverip+":9090/common/"+file_name
            self.assertTrue(file_exists(fileurl),"The microkernel file url could not found!")
            print "microkernel_list=",microkernel_list
        #time.sleep(60)
        micorkernel_json_list=list_microkernel()
        for kernelurl in microkernel_list:
            found_flag=False
            for microkernel in micorkernel_json_list:
                if microkernel["name"]==kernelurl:
                    found_flag=True
                    break
            self.assertTrue(found_flag,"microkernel with name: "+kernelurl+" not found!")
        print "Found all microkernels, list is correct!"

    def test_delete_microkernels(self):
        microkernel_list=list_microkernel()
        serverip=os.getenv("IMAGESERVER", "localhost")
        for microkernel in microkernel_list:
            self.assertNotEqual(delete_microkernel(microkernel["name"]),"fail","delete image failed!")
            fileurl="http://"+serverip+":9090/common/"+microkernel["name"]
            self.assertFalse(file_exists(fileurl),"The kernel image does not deleted completely")
        microkernel_list_clear=list_microkernel()
        self.assertTrue(microkernel_list_clear==[])
        print "All microkernels are cleared!"

    def test_rediscover(self):
        #Select one node at random that's not a management server
        self.test_upload_list_microkernel()
        NODECATALOG = fit_common.node_select()
        NODE = ""
        for dummy in NODECATALOG:
            NODE = NODECATALOG[random.randint(0, len(NODECATALOG)-1)]
            if fit_common.rackhdapi('/api/2.0/nodes/' + NODE)['json']['name'] != "Management Server":
                break
        if fit_common.VERBOSITY >= 2:
            print 'Checking OBM setting...'
        node_obm= fit_common.rackhdapi('/api/2.0/nodes/'+NODE)['json']['obms']
        if node_obm==[]:
            self.assertTrue(apply_obmsetting(NODE),"Fail to apply obm setting!")
        node_uuid= fit_common.rackhdapi('/redfish/v1/Systems/'+NODE)['json']['UUID']
        if fit_common.VERBOSITY >= 2:
            print 'UUID of selected Node is:'+node_uuid
        if fit_common.VERBOSITY >= 2:
            print 'Running rediscover, resetting system node...'
        #Reboot the node to begin rediscover.
        resetresponse = fit_common.rackhdapi('/redfish/v1/Systems/'+NODE+'/Actions/ComputerSystem.Reset',action='post',
                                            payload={"reset_type": "ForceRestart"})
        self.assertTrue(resetresponse['status']<209, 'Incorrect HTTP return code, expected <209 , got:' + str(resetresponse['status']))
        #Delete original node
        for dummy in range (0,20):
            time.sleep(1)
            result = fit_common.rackhdapi('/api/2.0/nodes/'+ NODE,action='delete')
            if result['status']<209:
                break
        self.assertTrue(result['status']<209, 'Was expecting response code < 209. Got ' + str(result['status']))
        print "Waiting node reboot and boot into microkernel........"
        self.assertTrue(wait_for_discover(node_uuid),"Fail to find the orignial node after reboot!")
        print "Found the orignial node. It is rediscovered succesfully!"

if __name__ == '__main__':
    fit_common.unittest.main()