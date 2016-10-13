'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

'''

import os
import sys
import subprocess
import urllib2
import string
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common
import time

# Select test group here using @attr
from nose.plugins.attrib import attr
@attr(all=True, regression=True, smoke=True)
class test_rackhd11_api_skupack(fit_common.unittest.TestCase):
    def setUp(self):
        api_data = fit_common.rackhdapi('/api/1.1/skus/')
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def ping_node_by_id(self,id):
        response_data = fit_common.rackhdapi("/api/1.1/nodes/" + id)
        mac=response_data['json']["name"]
        print "mac found=",mac
        catalogdata=fit_common.rackhdapi("/api/1.1/nodes/" + id+ "/catalogs/ohai/")
        ip=catalogdata['json']["data"]["ipaddress"]
        print "find ip=",ip
        if fit_common.remote_shell('ping -c 1 '+ip)['exitcode'] == 0:
            print "Successed, She is alive!"
            return 0
        else :
            print "Ping fail!"
            return 1

    def rackhd_api_11_create_skupack(self,skutype):
        url = fit_common.GLOBAL_CONFIG["repos"]["skupacks"][skutype]
        print "downloading url=",url
        file_name = url.split('/')[-1]
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
        f = open(file_name, 'rb')
        api_data = fit_common.rackhdapi('/api/1.1/skus/', action='binary-post',payload=f)
        self.assertEqual(api_data['status'], 201, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        foundflag=0
        api_response= fit_common.rackhdapi('/api/1.1/skus/')
        for item in api_response['json']:
            if skutype in item['name']:
                foundflag+=1
        self.assertEqual(foundflag,1,'Could not get the newly added sku info!')




    def rackhd_api_11_update_skupack(self,skutype):
        url = fit_common.GLOBAL_CONFIG["repos"]["skupacks"][skutype]
        print "downloading url=",url
        file_name = url.split('/')[-1]
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
        f = open(file_name, 'rb')
        api_data = fit_common.rackhdapi('/api/1.1/skus/')
        for item in api_data['json']:
            if skutype in item['name']:
                api_response = fit_common.rackhdapi('/api/1.1/skus/'+ item['id']+'/pack', action='binary-put',payload=f)
                self.assertEqual(api_response['status'], 201, 'Incorrect HTTP return code, expected 200, got:' + str(api_response['status']))


    def rackhd_api_11_post_firmware_file(self,skutype,updatetype):
        url = fit_common.GLOBAL_CONFIG["repos"]["firmware"][skutype][updatetype]
        print "downloading url=",url
        file_name = url.split('/')[-1]
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
        f = open(file_name, 'rb')

        api_response = fit_common.rackhdapi('/api/1.1/files/'+file_name, action='binary-put',payload=f)
        self.assertEqual(api_response['status'], 201, 'Incorrect HTTP return code, expected 200, got:' + str(api_response['status']))



    def test_api_11_sku_delete(self):
        # delete Quanta skus before test
        api_data = fit_common.rackhdapi("/api/1.1/skus")
        for item in api_data['json']:
            if "Quanta T41" in item['name'] or "Quanta T41" in item['name'] :
                fit_common.rackhdapi("/api/1.1/skus/" + item['id'], action="delete")

    def reboot_node(self,node_id):
        api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + node_id +'/Actions/ComputerSystem.Reset',action='post',payload={ "reset_type": "ForceRestart"})
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))

    def check_system_state(self,node_id):
        api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + node_id )
        self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        if api_data['json']['PowerState']!= "On":
            time.sleep(120)
            api_data = fit_common.rackhdapi('/redfish/v1/Systems/' + node_id )
            self.assertEqual(api_data['status'], 200, 'Incorrect HTTP return code, expected 200, got:' + str(api_data['status']))
        self.assertEqual(api_data['json']['PowerState'], "On", 'System is not on')
        #self.assertEqual(api_data['json'][ "Status"]['Health'], "OK", 'System health is not OK or unknown')
        try:
            if api_data['json'][ "Status"]['Health']!="OK":
                print "Warning! System health is not OK"
        except:
             print "Warning! System health is unknown!"


    def rackhd_api_11_skupack_firmware_update(self,skutype,updatetype,myaction):
        # delete Quanta skus before test
        api_data = fit_common.rackhdapi("/api/1.1/skus")
        if updatetype=="quantabios" or updatetype=="quantabmc":
            url= fit_common.GLOBAL_CONFIG["repos"]["firmware"][skutype]["bios"]
            biosimgfile=url.split('/')[-1]
            print "file_name=",biosimgfile
            url=fit_common.GLOBAL_CONFIG["repos"]["firmware"][skutype]["bmc"]
            bmcimgfile= url.split('/')[-1]
            print "file_name=",bmcimgfile
            intelimgfile=""
        else:
            biosimgfile=""
            bmcimgfile=""
            url=fit_common.GLOBAL_CONFIG["repos"]["firmware"][skutype]["firmware"]
            intelimgfile= url.split('/')[-1]
        graphlist={"intel":"Graph.Flash.Intel.Firmware",
                   "quantabios":"Graph.Flash.Quanta.BIOS",
                   "quantabmc":"Graph.Flash.Quanta.Bmc"}
        optionlist={"intel":"upgrade-firmware",
                   "quantabios":"upgrade-bios-firmware",
                   "quantabmc":"upgrade-bmc-firmware"}
        imgfile={"intel":intelimgfile,
                   "quantabios":biosimgfile,
                   "quantabmc":bmcimgfile}
        payloadlist={"dhcp+reboot": {"name":  graphlist[updatetype], "options": {"when-reboot-at-end": { "rebootAtEnd": "true" }}},
         "static+reboot": {"name": graphlist[updatetype],"options": {"when-reboot-at-end": { "rebootAtEnd": "true" }}},
         "dhcp+noreboot": { "name": graphlist[updatetype]},
         "static+noreboot":{ "name": graphlist[updatetype]},
         #"fileoveride": { "name":graphlist[updatetype], "options": { optionlist[updatetype]:{"file":imgfile[updatetype]},"when-reboot-at-end": { "rebootAtEnd": "true" }}},
         "fileoveride": { "name": graphlist[updatetype], "options": { optionlist[updatetype]:{"file":imgfile[updatetype]},"when-reboot-at-end": { "rebootAtEnd": "true" }}}          }
        #print "text=",api_data['json']
        for item in api_data['json']:
            print "item name=",item['name']
            print "item body=",item
            if skutype in item['name'] :
                if 'skuConfig' in item:
                    print "image name=",item['skuConfig']['biosFirmware']['filename']
                    if ".BIN" in item['skuConfig']['biosFirmware']['filename'] or ".bin" in item['skuConfig']['biosFirmware']['filename'] or ".ZIP" in item['skuConfig']['biosFirmware']['filename'] or ".zip" in item['skuConfig']['biosFirmware']['filename'] :
                        response_data = fit_common.rackhdapi("/api/1.1/skus/" + item['id']+ "/nodes")
                        for quantanode in response_data['json']:
                            quanta_node_id=quantanode['id']
                            catalogdata=fit_common.rackhdapi("/api/1.1/nodes/" +quanta_node_id)
                            bmc_ip=catalogdata['json']["obmSettings"][0]["config"]["host"]
                            fit_common.rackhdapi('/api/1.1/nodes/' + quanta_node_id + '/workflows/active', action='delete')
                            updatebios_data = fit_common.rackhdapi('/api/1.1/nodes/'+quanta_node_id+'/workflows', action='post',payload=payloadlist[myaction])
                            self.assertEqual(updatebios_data['status'], 201, 'Incorrect HTTP return code, expected 200, got:' + str(updatebios_data['status']))
                            workflow_id=updatebios_data['json']['instanceId']
                            self.wait_complete(workflow_id)
                            if myaction=="static+noreboot" or  myaction=="dhcp+noreboot":
                                self.assertEqual(self.ping_node_by_id(quanta_node_id), 0,'Could Not Ping to the node now!')
                                self.reboot_node(quanta_node_id)
                            time.sleep(120)
                            self.check_system_state(quanta_node_id)
                            #check if static ip is changed
                            if myaction=="static+noreboot" or  myaction=="static+reboot" or "fileoveride":
                                self.assertEqual(fit_common.remote_shell('ping -c 1 '+bmc_ip)['exitcode'],0,"Orignial BMC IP could not be ping through!")
                                if  updatetype!="quantabios":
                                    catalogdata=fit_common.rackhdapi("/api/1.1/nodes/" + quanta_node_id+ "/catalogs/bmc/")
                                    if catalogdata['json']["data"]["IP Address"]=="0.0.0.0":
                                        catalogdata=fit_common.rackhdapi("/api/1.1/nodes/" + quanta_node_id+ "/catalogs/rmm/")
                                        self.assertEqual(catalogdata['json']["data"]["IP Address"],bmc_ip,"Static IP is changed!")
                                    else:
                                        self.assertEqual(catalogdata['json']["data"]["IP Address"],bmc_ip,"Static IP is changed!")
                        return 0
                    else :
                        self.assertEqual(0,1,'No valid firmware image in skupack!')
                        return 1
                else:
                    self.assertEqual(0,1,'No valid firmware image in skupack!')
                    return 1
    '''
    def rackhd_api_11_quanta_skupack_bmc_update(self,skutype,myaction):
            # delete Quanta skus before test
            api_data = fit_common.rackhdapi("/api/1.1/skus")
            payloadlist={"dhcp+reboot": {"name": "Graph.Flash.Quanta.Bmc", "options": {"when-reboot-at-end": { "rebootAtEnd": "true" }}},
                     "static+reboot": {"name": "Graph.Flash.Quanta.Bmc","options": {"when-reboot-at-end": { "rebootAtEnd": "true" }}},
                     "dhcp+noreboot": { "name": "Graph.Flash.Quanta.Bmc"},
                     "static+noreboot":{ "name": "Graph.Flash.Quanta.Bmc"}   }

            #print "text=",api_data['json']
            for item in api_data['json']:
                print "item name=",item['name']
                print "item body=",item
                if skutype in item['name'] :
                    if 'skuConfig' in item:
                        print "image name=",item['skuConfig']['bmcFirmware']['filename']
                        if ".IMA" in item['skuConfig']['bmcFirmware']['filename'] or ".ima" in item['skuConfig']['bmcFirmware']['filename']:
                            response_data = fit_common.rackhdapi("/api/1.1/skus/" + item['id']+ "/nodes")
                            for quantanode in response_data['json']:
                                quanta_node_id=quantanode['id']
                                catalogdata=fit_common.rackhdapi("/api/1.1/nodes/" +quanta_node_id+ "/catalogs/bmc/")
                                bmc_ip=catalogdata['json']["data"]["IP Address"]
                                fit_common.rackhdapi('/api/1.1/nodes/' + quanta_node_id + '/workflows/active', action='delete')
                                updatebios_data = fit_common.rackhdapi('/api/1.1/nodes/'+quanta_node_id+'/workflows', action='post',payload= payloadlist[myaction])
                                self.assertEqual(updatebios_data['status'], 201, 'Incorrect HTTP return code, expected 200, got:' + str(updatebios_data['status']))
                                workflow_id=updatebios_data['json']['instanceId']
                                self.wait_complete(workflow_id)
                                if myaction=="static+noreboot" or  myaction=="dhcp+noreboot":
                                    self.assertEqual(self.ping_node_by_id(quanta_node_id), 0,'Could Not Ping to the node now!')
                                    self.reboot_node(quanta_node_id)
                                time.sleep(120)
                                self.check_system_state(quanta_node_id)
                                #check if static ip is changed
                                if myaction=="dhcp+noreboot" or  myaction=="dhcp+noreboot":
                                    self.assertEqual(fit_common.remote_shell('ping -c 1 '+bmc_ip)['exitcode'],0,"Orignial BMC IP could not be ping through!")
                                    catalogdata=fit_common.rackhdapi("/api/1.1/nodes/" + quanta_node_id+ "/catalogs/bmc/")
                                    self.assertEqual(catalogdata['json']["data"]["IP Address"],bmc_ip,"Static IP is changed!")
                            return 0
                        else :
                            self.assertEqual(0,1,'No valid firmware image in skupack!')
                            return 1
                    else:
                        self.assertEqual(0,1,'No valid firmware image in skupack!')
                        return 1
    '''

    def wait_complete(self,workflow_id):
        rc={}
        for dummy in range(0, 60):
            rc = fit_common.rackhdapi('/api/1.1/workflows/'+workflow_id)
            self.assertEqual(rc['status'], 200 , 'Incorrect HTTP return code, expected 200, got:' + str(rc['status']))
            if rc['json']['_status']=="succeeded" or rc['json']['_status']=="exception" or rc['json']['_status']=="failed":
                break
            else:
                if fit_common.VERBOSITY >= 6:
                    print time.strftime('%X %x %Z'),"current status:",rc['json']['_status']," Retry times:", dummy
                fit_common.time.sleep(30)
        #if rc['json']['_status']!="succeeded"
        #    fit_common.rackhdapi('/api/current/nodes/' + workflow_id + '/workflows/active', action='delete')
        self.assertEqual( rc['json']['_status'],"succeeded",' operation is not succeeded! we get '+str(rc['json']['_status']))



    #Test cases
    def test_api_11_create_quanta_t41_skupack(self):
        self.rackhd_api_11_create_skupack("Quanta T41")

    def test_api_11_create_quanta_d51_2u_skupack(self):
        self.rackhd_api_11_create_skupack("Quanta D51 2U")

    def test_api_11_update_quanta_t41_skupack(self):
        self.rackhd_api_11_update_skupack("Quanta T41")

    def test_api_11_update_quanta_d51_2u_skupack(self):
        self.rackhd_api_11_update_skupack("Quanta D51 2U")

    def test_api_11_update_rinjin_kp_skupack(self):
        self.rackhd_api_11_update_skupack("Rinjin KP")

    def test_api_11_update_rinjin_tp_skupack(self):
        self.rackhd_api_11_update_skupack("Rinjin TP")

    def test_api_11_update_hydra_skupack(self):
        self.rackhd_api_11_update_skupack("Hydra")

    def test_api_11_quanta_t41_skupack_firmware_update_static_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabios","static+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabmc","static+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')

    def test_api_11_quanta_t41_skupack_firmware_update_dhcp_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabios","dhcp+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabmc","dhcp+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')

    def test_api_11_quanta_t41_skupack_firmware_update_static_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabios","static+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabmc","static+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')

    def test_api_11_quanta_t41_skupack_firmware_update_dhcp_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabios","dhcp+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabmc","dhcp+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')

    def test_api_11_quanta_d51_2u_skupack_firmware_update_static_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabios","static+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabmc","static+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 failed!')

    def test_api_11_quanta_d51_2u_skupack_firmware_update_static_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabios","static+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabmc","static+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 failed!')

    def test_api_11_quanta_d51_2u_skupack_firmware_update_dhcp_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabios","dhcp+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabmc","dhcp+noreboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 failed!')

    def test_api_11_quanta_d51_2u_skupack_firmware_update_dhcp_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabios","dhcp+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 2U failed!')
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabmc","dhcp+reboot")
        self.assertEqual(responsecode, 0,'Update Quanta D51 2U failed!')

    def test_api_11_quanta_d51_2u_skupack_firmware_update_fileoveride(self):
        self.rackhd_api_11_post_firmware_file("Quanta D51 2U","bios")
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabios","fileoveride")
        self.assertEqual(responsecode, 0,'Update Quanta D51 failed!')
        self.rackhd_api_11_post_firmware_file("Quanta D51 2U","bmc")
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta D51 2U","quantabmc","fileoveride")
        self.assertEqual(responsecode, 0,'Update Quanta D51 2U failed!')
    
    def test_api_11_quanta_t41_skupack_firmware_update_fileoveride(self):
        self.rackhd_api_11_post_firmware_file("Quanta T41","bios")
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabios","fileoveride")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')
        self.rackhd_api_11_post_firmware_file("Quanta T41","bmc")
        responsecode= self.rackhd_api_11_skupack_firmware_update("Quanta T41","quantabmc","fileoveride")
        self.assertEqual(responsecode, 0,'Update Quanta T41 failed!')
    
    
    '''intel server''' 
    '''Hydra server''' 
    def test_api_11_hydra_skupack_firmware_update_static_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Hydra","intel","static+noreboot")
        self.assertEqual(responsecode, 0,'Update Hydra failed!')

    def test_api_11_hydra_skupack_firmware_update_static_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Hydra","intel","static+reboot")
        self.assertEqual(responsecode, 0,'Update Hydra failed!')

    def test_api_11_hydra_skupack_firmware_update_dhcp_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Hydra","intel","dhcp+noreboot")
        self.assertEqual(responsecode, 0,'Update Hydra failed!')

    def test_api_11_hydra_skupack_firmware_update_dhcp_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Hydra","intel","dhcp+reboot")
        self.assertEqual(responsecode, 0,'Update Hydra failed!')

    def test_api_11_hydra_skupack_firmware_update_fileoveride(self):
        self.rackhd_api_11_post_firmware_file("Hydra","firmware")
        responsecode= self.rackhd_api_11_skupack_firmware_update("Hydra","intel","fileoveride")
        self.assertEqual(responsecode, 0,'Update Hydra failed!')

    '''intel Rinjin KP server'''
    def test_api_11_rinjin_kp_skupack_firmware_update_static_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin KP","intel","static+noreboot")
        self.assertEqual(responsecode, 0,'Update Rinjin KP failed!')


    def test_api_11_rinjin_kp_skupack_firmware_update_static_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin KP","intel","static+reboot")
        self.assertEqual(responsecode, 0,'Update Rinjin KP failed!')

    def test_api_11_rinjin_kp_skupack_firmware_update_dhcp_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin KP","intel","dhcp+noreboot")
        self.assertEqual(responsecode, 0,'Update Rinjin KP failed!')

    def test_api_11_rinjin_kp_skupack_firmware_update_dhcp_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin KP","intel","dhcp+reboot")
        self.assertEqual(responsecode, 0,'Update Rinjin KP failed!')


    def test_api_11_rinjin_kp_skupack_firmware_update_fileoveride(self):
        self.rackhd_api_11_post_firmware_file("Rinjin KP","firmware")
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin KP","intel","fileoveride")
        self.assertEqual(responsecode, 0,'Update Rinjin KP failed!')

    '''intel Rinjin TP server'''
    def test_api_11_rinjin_tp_skupack_firmware_update_static_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin TP","intel","static+noreboot")
        self.assertEqual(responsecode, 0,'Update Rinjin TP failed!')


    def test_api_11_rinjin_tp_skupack_firmware_update_static_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin TP","intel","static+reboot")
        self.assertEqual(responsecode, 0,'Update Rinjin TP failed!')

    def test_api_11_rinjin_tp_skupack_firmware_update_dhcp_noreboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin TP","intel","dhcp+noreboot")
        self.assertEqual(responsecode, 0,'Update Rinjin TP failed!')

    def test_api_11_rinjin_tp_skupack_firmware_update_dhcp_reboot(self):
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin TP","intel","dhcp+reboot")
        self.assertEqual(responsecode, 0,'Update Rinjin TP failed!')


    def test_api_11_rinjin_tp_skupack_firmware_update_fileoveride(self):
        self.rackhd_api_11_post_firmware_file("Rinjin TP","firmware")
        responsecode= self.rackhd_api_11_skupack_firmware_update("Rinjin KP","intel","fileoveride")
        self.assertEqual(responsecode, 0,'Update Rinjin TP failed!')

    def test_check_system_state(self):
        self.check_system_state("57aacc6fd3d89e0e05513abe")
    ''' def test_find_microkernel(self):
            id="578857cd33ac86ba07fa9597"
            response_data = fit_common.rackhdapi("/api/1.1/nodes/" + id)
            mac=response_data['json']["name"]
            print "mac found=",mac
            catalogdata=fit_common.rackhdapi("/api/1.1/nodes/" + id+ "/catalogs/ohai/")
            ip=catalogdata['json']["data"]["ipaddress"]
            print "find ip=",ip
            if fit_common.remote_shell('ping -c 1 '+ip)['exitcode'] == 0:
                print "Successed, She is alive!"
            else :
                print "Ping fail!"'''
