'''
Copyright 2015, EMC, Inc.

Author(s):
George Paulos

This script installs OnRack packages onto blank VA.
'''

import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/fit_tests/common")
import fit_common

class onrack_package_install(fit_common.unittest.TestCase):
    def test01_install_onrack_packages(self):
        print "**** Installing OnRack Packages."
        quick_url = fit_common.GLOBAL_CONFIG['repos']['install']['onrack'] + "{0}".format(fit_common.ARGS_LIST['version'])
        shell_data = fit_common.remote_shell("wget -qO- '{0}' | bash".format(quick_url), timeout=900)
        self.assertEqual(shell_data['exitcode'], 0)

    def test02_post_install_reboot(self):
        print "**** Rebooting appliance."
        shell_data = fit_common.remote_shell("shutdown -r now")
        self.assertEqual(shell_data['exitcode'], 0, 'ORA reboot registered error')
        fit_common.countdown(90)
        print "**** Waiting for login."
        for dummy in range(0, 30):
            shell_data = fit_common.remote_shell("pwd")
            if shell_data['exitcode'] == 0:
                break
            else:
                fit_common.time.sleep(10)
        self.assertEqual(shell_data['exitcode'], 0, "Shell test failed after appliance reboot")

    def test03_check_install(self):
        print "**** Checking OnRack install."
        shell_data = fit_common.remote_shell("/opt/onrack/bin/monorail start")
        self.assertEqual(shell_data['exitcode'], 0, 'Monorail startup registered error')
        #retry 100 seconds for monorail up
        for dummy in range(0, 10):
            if fit_common.remote_shell("/opt/onrack/bin/monorail status")['exitcode'] == 0:
                break
            else:
                fit_common.time.sleep(10)
        self.assertEqual(shell_data['exitcode'], 0, 'Monorail status registered error')

    def test04_update_config(self):
        print "**** Updating OnRack config."
        hdconfig = fit_common.rackhdapi("/api/2.0/config")['json']
        hdconfig["httpProxies"] = [{
                        "localPath": "/mirror",
                        "remotePath": "/",
                        "server": fit_common.GLOBAL_CONFIG['repos']['mirror']
                    }]
        config_json = open('config.json', 'w')
        config_json.write(fit_common.json.dumps(hdconfig, sort_keys=True, indent=4))
        config_json.close()
        # copy files to ORA
        fit_common.scp_file_to_ora('config.json')
        self.assertEqual(fit_common.remote_shell('cp config.json /opt/onrack/etc/monorail.json')['exitcode'], 0, "OnRack Config file failure.")
        os.remove('config.json')
        shell_data = fit_common.remote_shell("/opt/onrack/bin/monorail restart")
        #retry 100 seconds for monorail up
        for dummy in range(0, 10):
            if fit_common.remote_shell("/opt/onrack/bin/monorail status")['exitcode'] == 0:
                fit_common.time.sleep(10)
                break
            else:
                fit_common.time.sleep(10)
        self.assertEqual(hdconfig, fit_common.rackhdapi("/api/2.0/config")['json'], "OnRack Config file failure.")

if __name__ == '__main__':
    fit_common.unittest.main()
