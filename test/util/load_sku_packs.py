'''
Copyright 2016, EMC, Inc.

Author(s):

This script load SKU packs from sources specified in install_default.json
'''

import fit_path  # NOQA: unused import
import os
import sys
import subprocess

import fit_common

from nose.plugins.attrib import attr
@attr(all=True)

class fit_template(fit_common.unittest.TestCase):

    def test01_download_sku_packs(self):
        # Download SKU packs from GitHub
        rc = subprocess.call("rm -rf temp.sku; rm -rf on-skupack;mkdir -p on-skupack", shell=True)
        self.assertEqual(rc, 0, "Unable to make on-skupack directory")
        # download all SKU repos and merge into on-skupack
        for url in fit_common.fitskupack():
            print "**** Cloning SKU Packs from " + url
            subprocess.call("git clone " + url + " temp.sku", shell=True)
            subprocess.call('cp -R temp.sku/* on-skupack; rm -rf temp.sku', shell=True)

    def test02_build_sku_packs(self):
        # build build SKU packs
        for subdir, dirs, files in os.walk('on-skupack'):
            for skus in dirs:
                if skus not in ["debianstatic", ".git"] and os.path.isfile('on-skupack/' + skus + '/config.json'):
                    subprocess.call("cd on-skupack;mkdir -p " + skus + "/tasks " + skus + "/static "
                                    + skus + "/workflows " + skus + "/templates", shell=True)
                    subprocess.call("cd on-skupack; ./build-package.bash "
                                    + skus + " " + skus + " >/dev/null 2>&1", shell=True)
            break

    def test03_upload_sku_packs(self):
        # upload SKU packs to RackHD
        for subdir, dirs, files in os.walk('on-skupack/tarballs'):
            for skupacks in files:
                print "\n**** Loading SKU Pack for " + skupacks
                fit_common.rackhdapi("/api/2.0/skus/pack", action="binary-post",
                                     payload=file(fit_common.TEST_PATH + "on-skupack/tarballs/" + skupacks).read())
            break
        print "\n"

    def test04_verify_sku_packs(self):
        # check SKU directory against source files
        error_message = ""
        skulist = fit_common.json.dumps(fit_common.rackhdapi("/api/2.0/skus")['json'])
        for subdir, dirs, files in os.walk('on-skupack'):
            for skus in dirs:
                if skus not in ["debianstatic", ".git", "packagebuild", "tarballs"] and \
                   os.path.isfile('on-skupack/' + skus + '/config.json'):
                    try:
                        configfile = fit_common.json.loads(open("on-skupack/" + skus  + "/config.json").read())
                        # check if sku pack got installed
                        if configfile['name'] not in skulist:
                            print "FAILURE - Missing SKU: " + configfile['name']
                            error_message += "  Missing SKU: " + configfile['name']
                    except:
                        # Check if the sku pack config.json file is valid format, fails skupack install if invalid
                        print "FAILURE - Corrupt config.json in SKU Pack: " + str(skus) + " - not loaded"
                        error_message += "  Corrupt config.json in SKU Pack: " + str(skus)
            break
        self.assertEqual(error_message, "", error_message)

if __name__ == '__main__':
    fit_common.unittest.main()
