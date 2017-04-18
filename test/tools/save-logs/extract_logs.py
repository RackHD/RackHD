#!/usr/bin/python

'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.

ScriptName: extract_logs.py
Author(s): Brent Higgins, E Hohenstein
Initial date: 09/01/16

Purpose:
This script is intended to expand the tarball created from save_logs.py
into a target directory.
It will create the target dir, expand tarball, and chmod 777 all the directories
and included files to allow the user and others to easily read, add, delete as needed.

'''
import os
import errno
import tarfile
import time
import argparse

import shutil


def main():
    ARG_PARSER = argparse.ArgumentParser(description="Command Help")
    ARG_PARSER.add_argument("-pkg", default="None",
                            help=".tgz file to be extracted")
    ARG_PARSER.add_argument("-dir", default="None",
                            help="directory .tgz file is located and default extraction location")
    ARG_PARSER.add_argument("-output_dir", default="None",
                            help="optional directory to extract to, defaults to tgz location")

    # parse arguments to ARGS_LIST dict
    ARGS_LIST = ARG_PARSER.parse_args()
    if ARGS_LIST.pkg == "None":
        print("No package given, please provide a package with the -pkg flag")
        exit(1)
    if ARGS_LIST.dir == "None":
        print("No s(urce directory given, please provide the source directory with the -dir flag")
        exit(1)
    if ARGS_LIST.dir[-1] != "/":
        ARGS_LIST.dir = ARGS_LIST.dir + "/"
    if ARGS_LIST.output_dir == "None":
        out_dir = ARGS_LIST.dir
    else:
        if ARGS_LIST.output_dir[-1] != "/":
            ARGS_LIST.output_dir = ARGS_LIST.output_dir + "/"
        out_dir = ARGS_LIST.output_dir
        mk_datadir(out_dir, out_dir)
        pstr = ARGS_LIST.pkg.split("/")
        pn = pstr[-1]
        pkgname = pn.rstrip("\r")
        shutil.copy(ARGS_LIST.dir + pkgname, out_dir)
    print("Extracting to: {}".format(out_dir))
    extract_tgz_file_to_datadir(ARGS_LIST.pkg, out_dir)


def extract_tgz_file_to_datadir(pkginfo, logdir):
    '''
    This function extracts the gathered tarball into the target directory
    printing progress as it goes for the user.
    :param pkginfo: string returned from gather script
    :param logdir: full local path to bug directory
    : return
        True on success unpack of main tarball
        False on any error
    '''
    status = False
    pstr = pkginfo.split("/")
    nlen = len(pstr)
    pn = pstr[nlen - 1]
    pkgname = pn.rstrip("\r")

    # Check the log directory for the existance of the tarball
    tgzpkg = logdir + "/" + pkgname
    if os.path.isfile(tgzpkg) is True:
        # Extract the tarball
        if tarfile.is_tarfile(tgzpkg) is True:
            print("Extracting tarball.....")
            tar = tarfile.open(tgzpkg)
            tar.extractall(path=logdir)
            tar.close()
            time.sleep(2)
            unpack_tarballs(logdir + "/stack")
            status = True
        else:
            print("Error: Could not unpack tarfile {}".format(tgzpkg))
            status = False
    else:
        print("Error: Cannot find tarball {}".format(pkgname))
        status = False

    if status is True:
        chmod_logpath(logdir)

    return status


def unpack_tarballs(logdir):
    '''
    This function will walk the specified log directory and attempt to extract any tgz or tar files
    it finds.  No error returned, best effort.
    :param logdir: full local path to log directory
    '''
    # Walk the log directory to extrack tarfiles
    if os.path.isdir(logdir):
        my_files = os.listdir(logdir)
        for file in my_files:
            myfile = logdir + "/" + file
            try:
                tarfile.is_tarfile(myfile)
                tar = tarfile.open(myfile)
                tar.extractall(path=logdir)
                tar.close()
            except:
                # Check for error - if extracting the same log directory twice, an error is tossed on files
                # that are already extracted
                continue
    else:
        print("Directory does not exist {} ".format(logdir))


def chmod_logpath(logdir):
    '''
    This function will walk the specified log directory and attempt to chmod to readable by all, best effort
    We could add chown as an enhancement.
    :param logdir: full local path to log directory
    '''
    # Walk the log directory and chmod to 0777 for directories and 0666 for files
    if os.path.isdir(logdir):
        os.chmod(logdir, 0o777)
        for root, dirs, files in os.walk(logdir):
            for dname in dirs:
                try:
                    os.chmod(os.path.join(root, dname), 0o777)
                except:
                    continue
            for fname in files:
                if os.access(os.path.join(root, fname), os.X_OK) is True:
                    try:
                        os.chmod(os.path.join(root, fname), 0o777)
                    except:
                        continue
                else:
                    try:
                        os.chmod(os.path.join(root, fname), 0o666)
                    except:
                        continue


def handle_pexpect_error(child, errstr):
    print(errstr)
    print(child.before, child.after)
    child.terminate()


def mk_datadir(logdir, name):
    '''
    This function creates a dirctory name on the logserver or current dir path
    It currently will not overwrite an existing directory.
    :param logdir: full local path to bug directory
    :param odr: the odr number specified by the user
    : return
        True on success
        False on any error
    '''
    try:
        os.makedirs(logdir, 0o777)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(logdir):
            print("Error: Directory {} already exists.".format(logdir))
            print("Please use a new name, such as {}-1 or delete the existing one.".format(name))
            return False
    return True


if __name__ == "__main__":
    main()
