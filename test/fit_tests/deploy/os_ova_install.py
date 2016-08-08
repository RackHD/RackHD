'''
Copyright 2015, EMC, Inc.

Author(s):
George Paulos

This script installs blank OVA template.
'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common
import pdu_lib

class os_ova_install(fit_common.unittest.TestCase):
    def test01_install_ova_template(self):
        # Check for ovftool
        self.assertEqual(fit_common.subprocess.call('which ovftool', shell=True), 0, "FAILURE: 'ovftool' not installed.")
        # Ping for valid ESXi host
        self.assertEqual(fit_common.subprocess.call('ping -c 1 ' + fit_common.ARGS_LIST['hyper'], shell=True), 0, "FAILURE: ESXi hypervisor not found.")
        # Shutdown previous ORA
        if fit_common.subprocess.call('ping -c 1 ' + fit_common.ARGS_LIST['ora'], shell=True) == 0:
            fit_common.remote_shell('shutdown -h now')
            fit_common.time.sleep(5)
        # Run OVA installer
        self.install_vm()
        # Wait for reboot to complete
        try:
            fit_common.remote_shell("pwd")
        except IOError:
            self.fail("*** Login Error")
        # Sync time on ORA
        localdate = fit_common.subprocess.check_output("date +%s", shell=True)
        fit_common.remote_shell("/bin/date -s @" + localdate.replace("\n", "") +
                                 ";/sbin/hwclock --systohc")
    def install_vm(self):
        ovafile = fit_common.GLOBAL_CONFIG['repos']['install']['ova'] + "/ora-stack-" \
                  + str(fit_common.ARGS_LIST['stack']) + ".ova "
        # Run probe to check for valid OVA file
        rc = fit_common.subprocess.call("ovftool " + ovafile, shell=True)
        if rc > 0:
            fit_common.premature_exit('Invalid or missing OVA file: ' + ovafile, 255)
        # Run OVA installer
        cred_list = fit_common.GLOBAL_CONFIG['credentials']['hyper']
        # just using first entry in cred list, will implement a retry over list later
        uname = cred_list[0]['username']
        passwd = cred_list[0]['password']
        print '**** Deploying OVA file on hypervisor ' + fit_common.ARGS_LIST['hyper']
        rc = fit_common.subprocess.call("ovftool --X:injectOvfEnv --powerOn --overwrite "
                                         "--powerOffTarget --skipManifestCheck -q "
                                         "--net:'ADMIN'='VM Network' "
                                         "--net:'CONTROL'='Control Network' "
                                         "--net:'PDU'='PDU Network' "
                                         "--noSSLVerify "
                                         + ovafile
                                         + "vi://" + uname + ":" + passwd + "@"
                                         + fit_common.ARGS_LIST['hyper'], shell=True)
        # Check for successful completion
        if rc > 0:
            print 'OVA installer failed at host: ' + fit_common.ARGS_LIST['hyper']
        for dummy in range(0, 30):
            rc = fit_common.subprocess.call("ping -c 1 -w 5 " + fit_common.ARGS_LIST['ora'], shell=True)
            if rc == 0:
                break
            else:
                fit_common.time.sleep(10)
        if rc > 0:
            print 'OVA installer failed at host: ' + fit_common.ARGS_LIST['ora']

    def test02_power_off_nodes(self):
        print "**** Configuring power interface: "
        self.assertTrue(pdu_lib.config_power_interface(), "Failed to configure power interface")
        # ServerTech PDU case
        if pdu_lib.check_pdu_type() != "Unknown":
            print "**** Installing snmp package: "
            self.assertTrue(pdu_lib.install_snmp(), "Failed to install snmp")
            print "**** PDU found, powering off compute nodes."
            self.assertTrue(pdu_lib.pdu_control_compute_nodes("off"), 'Failed to power off all outlets')
        # no PDU case
        else:
            print '**** No supported PDU found, using IMPI to restart, some nodes may not discover.'

if __name__ == '__main__':
    fit_common.unittest.main()
