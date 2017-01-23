'''
Copyright 2016, EMC, Inc.

Author(s):
George Paulos

This script load SKU packs from sources specified in install_default.json
'''


import os
import sys
import subprocess
# set path to common libraries
sys.path.append(subprocess.check_output("git rev-parse --show-toplevel", shell=True).rstrip("\n") + "/test/common")
import fit_common

class load_sku_packs(fit_common.unittest.TestCase):
    def test01_preload_sku_packs(self):
        print "**** Processing SKU Packs"
        # Load SKU packs from GutHub
        subprocess.call("rm -rf temp.sku; rm -rf on-skupack", shell=True)
        os.mkdir("on-skupack")
        # download all SKU repos and merge into on-skupack
        for url in fit_common.fitskupacks():
            print "**** Cloning SKU Packs from " + url
            subprocess.call("git clone " + url + " temp.sku", shell=True)
            subprocess.call('cp -R temp.sku/* on-skupack; rm -rf temp.sku', shell=True)
        # build build SKU packs
        for subdir, dirs, files in os.walk('on-skupack'):
            for skus in dirs:
                if skus not in ["debianstatic", ".git"] and os.path.isfile('on-skupack/' + skus + '/config.json'):
                    subprocess.call("cd on-skupack;mkdir -p " + skus + "/tasks " + skus + "/static "
                                    + skus + "/workflows " + skus + "/templates", shell=True)
                    subprocess.call("cd on-skupack; ./build-package.bash "
                                    + skus + " " + skus + " >/dev/null 2>&1", shell=True)
            break
        # upload SKU packs to ORA
        print "**** Loading SKU Packs to server"
        for subdir, dirs, files in os.walk('on-skupack/tarballs'):
            for skupacks in files:
                print "\n**** Loading SKU Pack for " + skupacks
                fit_common.rackhdapi("/api/1.1/skus/pack", action="binary-post",
                                     payload=file(fit_common.TEST_PATH + "on-skupack/tarballs/" + skupacks).read())
            break
        print "\n"
        # check SKU directory against source files
        errorcount = 0
        skulist = fit_common.json.dumps(fit_common.rackhdapi("/api/2.0/skus")['json'])
        for subdir, dirs, files in os.walk('on-skupack'):
            for skus in dirs:
                if skus not in ["debianstatic", ".git", "packagebuild", "tarballs"] and os.path.isfile('on-skupack/' + skus + '/config.json'):
                    configfile = fit_common.json.loads(open("on-skupack/" + skus  + "/config.json").read())
                    if configfile['name'] not in skulist:
                        print "FAILURE - Missing SKU: " + configfile['name']
                        errorcount += 1
            break
        self.assertEqual(errorcount, 0, "SKU pack install error.")

    def test02_preload_default_sku(self):
        # Load default SKU for unsupported compute nodes
        print '**** Installing default SKU'
        payload = {
                        "name": "Unsupported-Compute",
                        "rules": [
                            {
                                "path": "bmc.IP Address"
                            }
                        ]
                    }
        api_data = fit_common.rackhdapi("/api/2.0/skus", action='post', payload=payload)

if __name__ == '__main__':
    fit_common.unittest.main()
