'''
Copyright 2015, EMC, Inc.

Author(s):
George Paulos

This script installs blank OVA templates into selected stack.
if numvms is greater than 1, MAC address installation on OVA is done by stack number convention

usage:
    python run_tests.py -stack <stack ID> -numvms <number> -test deploy/os_ova_install.py
    or
    python run_tests.py -stack <stack ID> -test deploy/os_ova_install.py
'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess
import fit_common
import pdu_lib

class os_ova_install(fit_common.unittest.TestCase):
    def deploy_ova(self,vm,uname,passwd,numvms,ovafile):
        print '**** Deploying OVA file on hypervisor ' + fit_common.fitargs()['hyper']
        rc = subprocess.call("ovftool --X:injectOvfEnv --overwrite "
                             "--powerOffTarget --skipManifestCheck -q "
                             "--net:'ADMIN'='VM Network' "
                             "--net:'CONTROL'='Control Network' "
                             "--net:'PDU'='PDU Network' "
                             "--name='ora-stack-" + fit_common.fitargs()['stack'] + "-" + str(vm) + "' "
                             "--noSSLVerify "
                             + ovafile
                             + " vi://" + uname + ":" + passwd + "@"
                             + fit_common.fitargs()['hyper'], shell=True)
        # Check for successful completion
        if rc > 0:
            print 'OVA installer failed at host: ' + fit_common.fitargs()['hyper'] + "Exiting..."
            sys.exit(255)

        # Wait for VM to settle
        fit_common.countdown(30)

        # check number of vms for deployment
        if numvms == 1:
            ovamac = fit_common.fitcfg()['ovamac']
        else:
            # compose appropriate MAC address using lab convention
            vmnum = '{0:02}'.format(int(vm))
            macsplit = fit_common.fitcfg()['ovamac'].split(":")
            ovamac = macsplit[0] + ":" + macsplit[1] + ":" + macsplit[2] + ":" + macsplit[3] + ":" + macsplit[4] + ":"  + vmnum
        # Install MAC address by editing OVA .vmx file, then startup VM
        esxi_command = "export fullpath=`find vmfs -name ora-stack-" + fit_common.fitargs()['stack'] + "-" + str(vm) + "*.vmx`;" \
                       "for file in $fullpath;" \
                       "do " \
                       "export editline=`cat $file |grep \\\'ethernet0.generatedAddress =\\\'`;" \
                       "export editcmd=\\\'/\\\'$editline\\\'\/ c\\\ethernet0.address = \\\"" + ovamac + "\\\"\\\';" \
                       "sed -i \\\"$editcmd\\\" $file;" \
                       "sed -i \\\'/ethernet0.addressType = \\\"vpx\\\"/ c\\\ethernet0.addressType = \\\"static\\\"\\\' $file;" \
                       "sed -i \\\'/ethernet0.addressType = \\\"generated\\\"/ c\\\ethernet0.addressType = \\\"static\\\"\\\' $file;" \
                       "done;" \
                       "sleep 5;" \
                       "export vmidstring=`vim-cmd vmsvc/getallvms |grep ora-stack-" + fit_common.fitargs()['stack'] + "-" + str(vm) +  "`;" \
                       "for vmid in $vmidstring;" \
                       "do " \
                       "vim-cmd vmsvc/power.on $vmid;" \
                       "exit $?;" \
                       "done;"

        (command_output, exitstatus) = \
            fit_common.pexpect.run(
                            "ssh -q -o StrictHostKeyChecking=no -t " + uname + "@"
                            + fit_common.fitargs()['hyper'] + " " + esxi_command,
                            withexitstatus=1,
                            events={"assword": passwd + "\n"},
                            timeout=20, logfile=sys.stdout)
        if exitstatus > 0:
            print "MAC address processing failed. Exiting..."
            sys.exit(255)

        # Poll the OVA via ping
        for dummy in range(0, 30):
            if vm > 0:
                hostname = "stack" + fit_common.fitargs()['stack'] + "-ora-" + str(vm) + ".admin"
            else:
                hostname = "stack" + fit_common.fitargs()['stack'] + "-ora.admin"
            rc = subprocess.call("ping -c 1 -w 5 " + hostname, shell=True)
            if rc == 0:
                break
            else:
                fit_common.time.sleep(10)
        self.assertEqual(rc, 0, "VM did not activate.")
        # Sync time on ORA
        localdate = fit_common.subprocess.check_output("date +%s", shell=True)
        fit_common.remote_shell("/bin/date -s @" + localdate.replace("\n", "") + ";/sbin/hwclock --systohc")
        return None

    def test01_install_ova_template(self):
        ovafile = fit_common.fitargs()['template']
        numvms = int(fit_common.fitargs()['numvms'])
        # Check for ovftool
        self.assertEqual(fit_common.subprocess.call('which ovftool', shell=True), 0, "FAILURE: 'ovftool' not installed.")
        # Ping for valid ESXi host
        self.assertEqual(fit_common.subprocess.call('ping -c 1 ' + fit_common.fitargs()['hyper'], shell=True), 0, "FAILURE: ESXi hypervisor not found.")

        # Run probe to check for valid OVA file
        rc = fit_common.subprocess.call("ovftool " + ovafile, shell=True)
        self.assertEqual(rc, 0,'Invalid or missing OVA file: ' + ovafile)

        # check for number of virtual machine
        self.assertTrue(numvms < 100, "Number of vms should not be greater than 99")

        # Shutdown previous ORA
        if fit_common.subprocess.call('ping -c 1 ' + fit_common.fitargs()['rackhd_host'], shell=True) == 0:
            fit_common.remote_shell('shutdown -h now')
            fit_common.time.sleep(5)

        # this clears the hypervisor ssh key from ~/.ssh/known_hosts
        subprocess.call(["touch ~/.ssh/known_hosts;ssh-keygen -R "
                         + fit_common.fitargs()['hyper']  + " -f ~/.ssh/known_hosts >/dev/null 2>&1"], shell=True)

        # Find correct hypervisor credentials by testing each entry in the list
        cred_list = fit_common.fitcreds()['hyper']
        for entry in cred_list:
            uname = entry['username']
            passwd = entry['password']
            (command_output, exitstatus) = \
                fit_common.pexpect.run(
                                "ssh -q -o StrictHostKeyChecking=no -t " + uname + "@"
                                + fit_common.fitargs()['hyper'] + " pwd",
                                withexitstatus=1,
                                events={"assword": passwd + "\n"},
                                timeout=20, logfile=None)
            if exitstatus == 0:
                break
        # Run OVA installer
        for vm in range(0, numvms):
            self.deploy_ova(vm,uname,passwd,numvms,ovafile)

    def test02_power_off_nodes(self):
        print "**** Configuring power interface: "
        self.assertTrue(pdu_lib.config_power_interface(), "Failed to configure power interface")
        fit_common.time.sleep(15)
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
