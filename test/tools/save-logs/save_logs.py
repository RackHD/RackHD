#!/usr/bin/python
'''
Copyright 2016-2017, DELL EMC

ScriptName:  save_logs.py
Author(s): Erika Hohenstein, Brent Higgins
Initial date: 07/10/15

Purpose:
Remotely run the rackhd_gather_info.py on a stack (or appliance, vagrant instances) and copy log
files to a target directory off box.
The script will create the target directory
A configuration file 'save_logs_conf.json' can be setup to provide the following information.
  user, password, webserver, local directory to store files
'''

import json
import argparse
import subprocess
import time
import sys
import os
import socket

try:
    import pexpect
except IOError:
    print("Python 'pexpect' package required for this script.")
    print("Use: 'pip install pexpect'\nExiting...\n")
try:
    import extract_logs
except IOError:
    print("Python \'extract_logs\' script required for this script, check for errors.")
    exit(1)

# Default gather script
gather_script = "rackhd_gather_info.py"

real_raw_input = vars(__builtins__).get('raw_input', input)


def main():
    myfile = os.path.basename(__file__)
    path = os.path.realpath(myfile)
    cur_dir = os.path.dirname(path)

    ARG_PARSER = argparse.ArgumentParser(description="Command Help")
    ARG_PARSER.add_argument("-v", action='store_true',
                            help="Turn on verbose mode")
    ARG_PARSER.add_argument("-ip", default="0.0.0.0",
                            help="Appliance IP address or hostname")
    ARG_PARSER.add_argument("-port", default="",
                            help="Optional port argument for scp/ssh")
    ARG_PARSER.add_argument("-user", default="None",
                            help="Appliance username")
    ARG_PARSER.add_argument("-pwd", default="None",
                            help="Appliance password")
    ARG_PARSER.add_argument("-no_extract", action='store_true',
                            help="Do not extract the tarball, default to extract")
    ARG_PARSER.add_argument("-log_path", default="None",
                            help="Logging Directory Path")
    ARG_PARSER.add_argument("-target_dir", default="None",
                            help="Target directory name to store logs")

    # parse arguments to ARGS_LIST dict
    ARGS_LIST = ARG_PARSER.parse_args()
    try:
        CONFIG = json.loads(open("save_logs_conf.json").read())
        print("save_logs: Using configuration from \"save_logs_conf.json\".")
        config = True
    except:
        print("save_logs: No config file found")
        config = False

    if ARGS_LIST.user == "None":
        try:
            ARGS_LIST.user = CONFIG["username"]
        except:
            if config is True:
                print("Username required")
                print("Usage: {0} -user <username>".format(myfile))
            else:
                print("Missing Required Parameters")
                print("Usage: ./save_logs.py -ip <ip> -user <username> -pwd <password>")
            sys.exit(-1)

    if ARGS_LIST.pwd == "None":
        try:
            ARGS_LIST.pwd = CONFIG["password"]
        except:
            if config is True:
                print("Password required")
                print("Usage: {0} -pwd <password>".format(myfile))
            else:
                print("Missing Required Parameters")
                print("Usage: ./save_logs.py -ip <ip> -user <username> -pwd <password>")
            sys.exit(-1)

    if ARGS_LIST.ip == "0.0.0.0":
        try:
            ARGS_LIST.ip = CONFIG["ip"]
        except:
            if config is True:
                print("Stack IP address or hostname required.")
                print("Usage: {0} -ip <ip or hostname>".format(myfile))
            else:
                print("Missing Required Parematers")
                print("Usage: ./save_logs.py -ip <ip> -user <username> -pwd <password>")
            sys.exit(-1)

    # scp requires a capital P, ssh requires a lowercase p, for port. Setting up the string format here.
    # necessary for vagrant instance log gathering.
    if ARGS_LIST.port != "":
        ARGS_LIST.port2 = "-P " + ARGS_LIST.port
        ARGS_LIST.port = "-p " + ARGS_LIST.port
    else:
        ARGS_LIST.port2 = ""

    # Check the log directory path exists, may be using a logserver so ensure it is there
    if not os.path.isdir(ARGS_LIST.log_path):
        try:
            ARGS_LIST.log_path = CONFIG["log_directory_path"]
            # check if value from config file is valid
            if not os.path.isdir(ARGS_LIST.log_path):
                print('Output directory path is not present on this system: {0}'.format(ARGS_LIST.log_path))
                print("Saving logs in current directory: {}".format(cur_dir))
                ARGS_LIST.log_path = cur_dir
            else:
                print('Saving logs in directory path: {}'.format(ARGS_LIST.log_path))
        except:
            print("Saving logs in current directory: {}".format(cur_dir))
            ARGS_LIST.log_path = cur_dir
    else:
        print('Saving logs in directory path: {}'.format(ARGS_LIST.log_path))

    # Get the target directory name, will get appended to the log path and created
    if ARGS_LIST.target_dir == "None":
        ARGS_LIST.name = real_raw_input("Enter name of target directory, will be created: ")
        print("Directory: {} ".format(ARGS_LIST.name))
    else:
        ARGS_LIST.name = ARGS_LIST.target_dir

    # setup connection to the stack/server
    setup_connection(ARGS_LIST)

    # Run the save logs function
    save_logs(ARGS_LIST)
    # If log server used, print(log location)
    try:
        if ARGS_LIST.log_path == CONFIG["log_directory_path"]:
            print("Webserver: {0}{1}".format(CONFIG["webserver"], ARGS_LIST.name))
    except:
        pass
    print("\n----Done----")


def save_logs(args):
    '''
    Function that runs the overall processs of gathering and retrieving
    all of the log information.
    This is outside of main in order to allow other scripts acess to this utility
    :param args: command line arguments
    '''
    print("This utility will attempt to gather log files and data from your appliance for debugging.")

    teststack = args.ip
    print("Pushing gather script to stack....")
    if copy_loggather_script_to_stack(teststack, args) is True:
        if args.log_path[-1] != "/":
            args.log_path = args.log_path + "/"
        logdir = args.log_path + args.name
        # make the log directory
        if extract_logs.mk_datadir(logdir, args.name) is True:
            print("Running gather logs script, please wait.....")
            pkg = run_gather_logs(teststack, args)
            if pkg != "none":
                print("Saved logs on stack in {}".format(pkg))
                print("Copying from stack....")
                if scp_tgz_to_logserver(teststack, pkg, logdir, args) is True:
                    if args.no_extract is False:
                        extract_logs.extract_tgz_file_to_datadir(pkg, logdir)
                print("Log directory: {}".format(logdir))
        else:
            print("Could not create Log directory \"" + logdir + "\"")

    # Attempt to clean up gather script from stack regardless
    remove_gather_script(teststack, args)


def copy_loggather_script_to_stack(testhost, args):
    '''
    Copies the script rackhd_gather_info.py from the tools/loggather directory to
    the stack in /tmp using pexpect.
    :param testhost: ip address of stack
    :param args: command line arguments
    :return:
        True on successful scp
        False on any error
    '''
    status = False
    # get there from here
    my_dir = os.path.dirname(os.path.abspath(__file__))

    command = "scp " + args.port2 + " " + "\"" + my_dir + "/" + gather_script \
              + "\"" + " " + args.user + "@" + testhost + ":/tmp/."
    child = pexpect.spawn(command)
    child.timeout = 10
    while True:
        i = child.expect(['assword: ', pexpect.TIMEOUT, pexpect.EOF])
        if i == 0:
            child.sendline(args.pwd)
            time.sleep(2)
            data = child.read()
            if "No such file" in data:
                print("ERROR: Failed to push " + gather_script +
                      " script to stack.\nCheck your repository contains " + my_dir + "/" + gather_script)
                status = False
                break
            else:
                status = True
                break
        elif i == 2 or i == 3:
            handle_pexpect_error(child, "ERROR: Failed to push gather script to stack.\nCheck access to stack.")
            status = False
            break
    child.close()
    return status


# cleanup, remove the script from the stack /tmp directory
def remove_gather_script(testhost, args):
    '''
    This function will remove the gather script from the stack to clean up
    It is a best effort to remove, so if it fails, will generate an message
    to the user to clean up manually
    :param testhost: ip address of stack
    :param args: command line arguments
    '''
    remote_ssh_res = {'stdout': "", 'exitcode': 0}
    str_remove_cmd = "rm /tmp/" + gather_script

    remote_ssh_res = remote_shell(str_remove_cmd, args)
    if remote_ssh_res['exitcode'] != 0:
        print("Error in remove command from " + testhost)
        print("Please clean up /tmp directory on stack")


def run_gather_logs(testhost, args):
    '''
    This function will run the rackhd_gather_info.py script on the stack via remote ssh.
    If the script runs successfully, the stdout of the script produces a message that
    we check for that includes the package name, in this form:
    Package: /tmp/rackhd/pkg/RackHDLogs-ora-20150715-232238.tgz
    :param testhost: ip address of rackhd server
    :param args: command line arguments
    :return:
        none as the package name on any failure
        package name in the form of /tmp/rackhd/.....tgz on success
    '''

    pkgfile = "none"
    remote_ssh_res = {'stdout': "", 'exitcode': 0}
    str_gather_cmd = "/tmp/" + gather_script

    remote_ssh_res = remote_shell(str_gather_cmd, args)
    if remote_ssh_res['exitcode'] != 0:
        print("Error in executing " + gather_script + " on " + testhost)
    else:
        pstr = remote_ssh_res['stdout']
        # the rackhd_gather_info.py script returns the package name in the output
        for row in pstr.split('\n'):
            if 'Package:' in row:
                pkgfile = row.split(': ')[1]
    return pkgfile


def scp_tgz_to_logserver(testhost, pkginfo, logdir, args):
    '''
    Using pexpect, this function will scp the tarfile specified in pkginfo from the
    testhost stack to the log directory.  The pkginfo contains the full path on the stack.
    :param testhost: ip address of rackhd server
    :param pkginfo: string returned from gather script
    :param logdir: full local path to bug directory
    :param args: command line arguments
    :return:
        True if scpcommanddoes not return an error
        False if an error in the scpcommandfailed
    '''
    status = False

    command = "scp " + args.port2 + " " + args.user + "@" + testhost + ":" + pkginfo + " " + logdir
    child = pexpect.spawn(command)
    child.timeout = 60
    i = child.expect(['assword: ', pexpect.TIMEOUT])
    if i == 0:
        child.sendline(args.pwd)
        # wait for scp to copy file
        time.sleep(10)
        status = True
    else:
        print(child.before)
        print("ERROR: Expecting password for SCP timed out.")
        print("SCP of log files failed due to password error.")
        print("Please manually scp " + pkginfo + " to desired location.")

    child.close()
    return status


def handle_pexpect_error(child, errstr):
    print(errstr)
    print(child.before, child.after)
    child.terminate()


def remote_shell(shell_cmd, args, expect_receive="", expect_send=""):
    '''
    Run ssh based shellcommandon a remote machine at args.ip
    :param shell_cmd: string based command
    :param expect_receive:
    :param expect_send:
    :param args: all command line arguments
    :return: dict = {'stdout': str:ouput, 'exitcode': return code}
    '''
    cmd_args = vars(args)

    logfile_redirect = None
    shell_cmd.replace("'", "\\\'")
    if args.v is True:
        print("remote_shell: Shell Command: {}".format(shell_cmd))
        logfile_redirect = sys.stdout
    if expect_receive == "" or expect_send == "":
        (command_output, exitstatus) = \
            pexpect.run("ssh -q -o StrictHostKeyChecking=no -t " + args.port + " " + cmd_args['user'] +
                        "@" + cmd_args['ip'] + " sudo sh -c \\\"" + shell_cmd + "\\\"",
                        withexitstatus=1,
                        events={"assword": cmd_args['pwd'] + "\n"},
                        timeout=600, logfile=logfile_redirect)
    else:
        (command_output, exitstatus) = \
            pexpect.run("ssh -q -o StrictHostKeyChecking=no -t " + args.port + " " + cmd_args['user'] +
                        "@" + cmd_args['ip'] + " sudo sh -c \\\"" + shell_cmd + "\\\"",
                        withexitstatus=1,
                        events={"assword": cmd_args['pwd'] + "\n",
                                expect_receive: expect_send + "\n"},
                        timeout=600, logfile=logfile_redirect)
    if args.v is True:
        print("Shell cmd: {}".format(shell_cmd))
        print("Exit Code: {}".format(exitstatus))
    return {'stdout': command_output, 'exitcode': exitstatus}


def setup_connection(args):
    '''
    This function will clear the stored ssh keys and check the connection to the host specified.
    If there is an issue connecting to the host the program will exit.
    :param args: all command line arguments
    '''
    subprocess.call(["touch ~/.ssh/known_hosts;ssh-keygen -R " + args.ip +
                     " -f ~/.ssh/known_hosts > /dev/null 2>&1"], shell=True)
    # if ip parameter is a hostname clear key associated with the ip as well as name
    try:
        subprocess.call(["touch ~/.ssh/known_hosts;ssh-keygen -R " +
                         socket.gethostbyname(args.ip) + " -f ~/.ssh/known_hosts > /dev/null 2>&1"], shell=True)
    except:
        pass
    command = 'ssh -t {0} {1}@{2} "echo connected"'.format(args.port, args.user, args.ip)
    child = pexpect.spawn(command)
    child.timeout = 5
    while True:
        i = child.expect(['yes/no', 'assword:', 'Permission denied', "connected",
                          'Could not resolve', 'no route', 'Invalid', pexpect.EOF, pexpect.TIMEOUT])
        if i == 0:     # Continue with new ssh key
            child.sendline('yes')
        elif i == 1:   # Asking for password
            child.sendline(args.pwd)
        elif i == 3:   # Connected to the host
            break
        else:
            print("ERROR: Unable to access host exiting...")
            exit(-1)


if __name__ == '__main__':
    main()
