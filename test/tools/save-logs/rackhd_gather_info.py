#!/usr/bin/python

# Copyright 2015, EMC, Inc.
# ex: set shiftwidth=4 tabstop=4 expandtab:
#
# 07/14/2015 ehohenstein
#
# This utility is based off of EMC Isilon's isi_gather_info script and
# all appreciation for the script can be directed to the original authors.
#
# The utility is intended to be installed onto the RackHD appliance
# to use and will gather a defined set of log files and output of
# commands, capturing all into a single tarfile.  The tarfile can
# then be placed off the applicance and extracted.
#
# The utiilty only makes use of the basic modules in this script to
# run commands and gather logs into the tarfile and storing them in the
# /tmp directory.  Reference to incremental builds, full and local
# log gathers, and groups are a hold over from the full version
# of this script.  Updates could be added back in to make uses of all
# the options.

import errno
import getopt
import os
import random
import re
import signal
import sys
import time
import threading
import traceback
import subprocess

# for package xml metadata
import xml.etree.ElementTree as etree

PROGNAME = os.path.basename(sys.argv[0])
REVISION = "Revision: 001"

try:
    True
except NameError:
    True = 1
    False = 0

SUPPORT_DIR = None
TMP_SUPPORT_DIR = None
LOCAL_TMP_SUPPORT_DIR = None
PKG_SUPPORT_DIR = None
GATHER_SCRIPT = None
PACKAGE_INFO = None
SAVED_COMMAND_LINE = None

_TMP_SUPPORT_DIR = 'tmp/'
_PKG_SUPPORT_DIR = 'pkg/'
_GATHER_SCRIPT = '_gather'
_LOCAL_GATHER_SCRIPT = '_stack_gather'
_LOCAL_TMP_SUPPORT_DIR = "stack"
_PACKAGE_INFO = 'package_info.xml'
_SAVED_COMMAND_LINE = 'command_line'
_FULLGATHER_FILE = 'last_full_gather'

VAR_SUPPORT_DIR = '/tmp/rackhd'

GATHER_STATUS_PATH = '/var/run/gather-status'
GATHER_STATUS_LOCK = GATHER_STATUS_PATH + '.lock'

CONFIGDIR = '/tmp'

# 'exe': cmd, name: cmd==command, name==output filename
# 'tar': cmd, name: cmd==cd to parent dir; name==tarball_filename tarball_dir
# See generate_scripts for the consumer of this information.
UTILITIES = {
    'var_log': ('tar', "cd /", "varlog.tar /var/log"),
    'pm2v_log': ('tar', "cd /home", "vagrant-pm2log.tar vagrant/.pm2"),
    'pm2o_log': ('tar', "cd /home", "onrack-pm2log.tar onrack/.pm2"),
    'pm2_status': ('exe', "${SUDO} pm2 status ", "pm2status"),
    # 'apache2status': ('exe', "${SUDO}service apache2 status", "apache2status"),
    # 'conductor': ('exe', "systemctl status conductor", "conductor_status"),
    'df': ('exe', "/bin/df -li", "df"),
    'dpkg_info': ('exe', "dpkg -l | grep \"ii  on\"", "dpkg_list"),
    'dhcp_leases': ('tar', "cd /var/lib", "varlib-dhcp.tar dhcp"),
    'etc': ('tar', "cd /etc", "etc_init.tar init.d"),
    'ipinfo': ('exe', "ip addr", "ipinfo"),
    'bash_history': ('tar', "cd /root", "bash_history.tar .bash_history"),
    'meminfo': ('exe', "/bin/cat /proc/meminfo", "meminfo"),
    'services': ('exe', "(service on-http status; echo;" \
                 "service on-tftp status; echo;" \
                 "service on-dhcp-proxy status; echo;" \
                 "service on-syslog status; echo;" \
                 "service on-taskgraph status;)", "services"),
    'mongodump': ('exe', "cd /var/log;/usr/bin/mongodump --out mongodumpdir", "mongodump"),
    'slabinfo': ('exe', "${SUDO} /bin/cat /proc/slabinfo", "slabinfo"),
    'top': ('exe', "/usr/bin/top -S -b -d 1 -n 3", "top"),
    'uname': ('exe', "/bin/uname -a", "uname"),
    'uptime': ('exe', "/usr/bin/uptime", "uptime"),
    'ps': ('exe', "/bin/ps auxxxx", "ps"),
    'netstat': ('exe', "(/bin/netstat -sn; echo; " \
                "/bin/netstat -rn; echo; " \
                "/bin/netstat -lan)", "netstat"),
}

# List of commands that are run
EXEMPT = [
    'var_log',
    # 'apache2status',
    # 'conductor',
    'dhcp_leases',
    'df',
    'dpkg_info',
    'etc',
    'ipinfo',
    'bash_history',
    'meminfo',
    'services',
    # 'monorail',
    'mongodump',
    'slabinfo',
    'top',
    'uname',
    'uptime',
    'pm2_status',
    'pm2v_log',
    'pm2o_log',
    'ps',
    'netstat',
]

# GROUPS holds the groups of utilities that can be specified by the
# not fully implemented yet
# --group command line option.
GROUPS = {
    "service": [
        # "conductor",
        # "conductor_2x",
        "services",
        # "monorail",
        # "apache2status",
    ],
    "system": [
        "ipinfo",
        "df",
        "top",
        "meminfo",
        "slabinfo",
        "top",
        "uname",
        "uptime",
        "dpkg_info",
    ],
    "network": [
        "ipinfo",
        "netstat",
    ],
    "logs": [
        "var_log",
    ],
}


class Stack:
    pass


class Options:
    pass


# Globals
stack = Stack()
options = Options()
log = ''    # used later on to write to gather-status log file
re_upload = ''


def update_support_dirs(options):
    global SUPPORT_DIR
    global TMP_SUPPORT_DIR
    global PKG_SUPPORT_DIR
    global GATHER_SCRIPT
    global LOCAL_GATHER_SCRIPT
    global PACKAGE_INFO
    global SAVED_COMMAND_LINE
    global LOCAL_TMP_SUPPORT_DIR
    global FULLGATHER_FILE

    if options.tempdir:
        if options.tempdir[0] != '/':
            error("Only full path tempdir specifications allowed.")
        SUPPORT_DIR = options.tempdir
    else:
        SUPPORT_DIR = VAR_SUPPORT_DIR

    # generate a unique random tempdir. this is not safe against races, but
    # shouldn't need to be.
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    while True:
        tmpdir = ""
        for i in range(16):
            tmpdir += chars[random.randint(0, len(chars) - 1)]
        # this directory is expected to end in "/" elsewhere in the code, but
        # to verify that a file doesn't exist by the name of the directory
        # we wish to create, we have to check if the directory exists without
        # the trailing slash, first.
        TMP_SUPPORT_DIR = os.path.join(SUPPORT_DIR, _TMP_SUPPORT_DIR, tmpdir)
        if not os.path.exists(TMP_SUPPORT_DIR):
            TMP_SUPPORT_DIR += "/"
            break

    if options.tardir:
        PKG_SUPPORT_DIR = options.tardir
    else:
        PKG_SUPPORT_DIR = os.path.join(SUPPORT_DIR, _PKG_SUPPORT_DIR)

    FULLGATHER_FILE = os.path.join(SUPPORT_DIR, _FULLGATHER_FILE)
    GATHER_SCRIPT = os.path.join(TMP_SUPPORT_DIR, _GATHER_SCRIPT)
    LOCAL_GATHER_SCRIPT = os.path.join(TMP_SUPPORT_DIR, _LOCAL_GATHER_SCRIPT)
    PACKAGE_INFO = os.path.join(TMP_SUPPORT_DIR, _PACKAGE_INFO)
    SAVED_COMMAND_LINE = os.path.join(TMP_SUPPORT_DIR, _SAVED_COMMAND_LINE)
    LOCAL_TMP_SUPPORT_DIR = os.path.join(TMP_SUPPORT_DIR, _LOCAL_TMP_SUPPORT_DIR)

    # Make sure the dirs exist locally first
    makeDir(SUPPORT_DIR)
    makeDir(TMP_SUPPORT_DIR)
    makeDir(LOCAL_TMP_SUPPORT_DIR)
    makeDir(PKG_SUPPORT_DIR)


# this routine creates a local_gather script that is invoked locally on the stack.
# run_utils should be a list of the names of utilities in the UTILITIES dict.
def generate_scripts(run_utils):

    # rackhd always needs sudo to run
    rackhd_state = 1
    try:
        flags = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        header = "#!/bin/bash\nHOST=`hostname`\n"
        if rackhd_state == 0:
            pass
        else:
            header += "SUDO='sudo '\n"
            # print "Sudo header:", header

        localfd = os.open(LOCAL_GATHER_SCRIPT, flags, 0755)
        os.write(localfd, header)

        for util in run_utils:
            exe, cmd, name = UTILITIES.get(util)
            if exe == 'local_tar' or exe == 'tar':
                line = "%s;/bin/tar cf %sstack/%s 1>/dev/null 2>&1" % \
                    (cmd, TMP_SUPPORT_DIR, name.lstrip())
            elif exe == 'local_exe' or exe == 'exe':
                line = "%s 1> %sstack/%s 2>&1" % \
                    (cmd, TMP_SUPPORT_DIR, name.lstrip())
            else:
                line = ''

            line += "\n"

            # write the script file for the local stack
            os.write(localfd, line)

        # script must exit cleanly
        footer = "exit 0\n"

        os.write(localfd, footer)
        os.close(localfd)

    except OSError, (errno, strerror):
        error("OS error: %s" % os.strerror(errno))


# assumptions:
#   the server has enough free space to store the temporary info in /tmp in
#   files and the final compressed package (about 100MB needed, usually
#   determined by the size of /var/log/).
#
def main():
    global stack, options, log, re_upload

    # print "GATHER_STATUS_PATH:", GATHER_STATUS_PATH
    log = Logger(GATHER_STATUS_PATH)

    #
    # don't treat ^C special
    # and ignore the HUP signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    # internal correctness check
    validateUtils()

    stack.name = None
    stack.hostname = None
    stack.user = None
    stack.password = None
    stack.nodes = []

    options.gather_script = []
    options.gather_expr = []

    options.includes = []
    options.noconfig = True
    options.local_only = True
    options.tardir = None
    options.tarfile = None
    options.tempdir = None
    options.no_exempt_logs = False
    options.debug = False
    options.verbose = False
    options.group = []
    options.group_utils = []

    # Allow all directory and data creation to be accessed by the group users
    os.umask(0002)

    # parse options
    get_options()

    if stack.password:
        print "\nNote: A password is only required with -T.  Ignoring."

    # update paths
    update_support_dirs(options)

    # Get the stack name
    stack.name, stack.hostname = getHostname()

    saveCommandLine()

    # Convert -f filenames to UTILITIES commands; Add to UTILITIES
    # Convert gather_script/_expr to UTILITIES commands; Add to UTILITIES
    # Create include_list using the final updated UTILITIES.
    if "all" in options.includes:
        include_list = UTILITIES.keys()
    else:
        include_list = options.includes

    # write the temp script that contains the instructions for information
    # gathering.  we're going to write this in TMP_SUPPORT_DIR,
    # so we need to 1) see if that dir already exists, and 2) create it
    # (and any parents) if it doesn't exist.
    #
    # note that the gathered information from the stack is temporary
    # and will be removed at the end of the script.  however, the final
    # package file (stored in PKG_SUPPORT_DIR, or specified tarfile path)
    # will be uniquely preserved.
    #
    # NOTE: The paths created here for the nodes MUST match those
    #       utilized in the generate_scripts routine.
    dirs = [SUPPORT_DIR, TMP_SUPPORT_DIR, PKG_SUPPORT_DIR,
            LOCAL_TMP_SUPPORT_DIR]

    count = makeDirs(dirs)
    if count:
        error("FAILED to make required directories on %d nodes." % count)

    try:
        last_full_gather = int(os.stat(FULLGATHER_FILE).st_mtime)
    except:
        last_full_gather = 0

    # build the gather script, based on the known information gathering
    # utilities, and the utilities the user is wishing to include
    run_utils = buildRunUtils(include_list)
    if len(run_utils) == 0:
        error("No commands or info found to gather")

    generate_scripts(run_utils)

    # run everything.
    start_time = int(time.time())
    exit_status = 0

    print "Running gather script."
    print "This may take several minutes.  Please do not interrupt the script."
    print

    log.write("Gather In Progress on stack. Running.")
    task = "Running gather script on stack"
    (exit, output) = get_cmd_output("bash " + LOCAL_GATHER_SCRIPT)
    if exit:
        print "ERROR %s" % task
        log.write("Gather Failed. %s" % output)
        for line in output:
            print line

    # Save package xml metadata
    pkginfo = {
        "gather_date": start_time,
        "last_full": last_full_gather,
    }

    # if this generation fails, we can continue, but dump traceback info
    try:
        savePackageInfo(pkginfo, PACKAGE_INFO)
    except Exception, e:
        try:
            traceback.print_exc(file=open(PACKAGE_INFO, 'a'))
        except:
            pass

    # put everything into one tarball
    log.write("Gather Succeeded.")
    print "Information gathering completed... creating compressed package."
    pkg_path_name = makePkgName()

    try:
        tar_command = "/bin/tar czf %s . 2>&1" % pkg_path_name
        os.chdir(TMP_SUPPORT_DIR)
        (exit, output) = get_cmd_output(tar_command)
        if exit:
            print "ERROR tar returned %d" % (exit >> 8),
            log.write("Gather Failed")
            if output:
                print ", output follows:"
                for line in output:
                    print line
            else:
                print ""
            error("Could not create compressed package.")
            log.write("Gather Failed. Could not create compressed package.")
    except OSError, (errno, strerror):
        error("FAILED system call (tar): %s" % (os.strerror(errno)))
        log.write("Gather Failed %s" % (os.strerror(errno)))

    print "Packaging complete..."
    print "Package: %s" % pkg_path_name
    log.write("Package: %s" % pkg_path_name)

    # If we don't have the exit_status set, then the log gathered
    # completely
    if not exit_status:
        if not os.path.exists(FULLGATHER_FILE):
            try:
                fullgather = open(FULLGATHER_FILE, 'w')
                fullgather.write('This space intentionally left blank.\n')
                fullgather.close()
            except:
                sys.stderr.write('WARNING: Full Gather run data not recorded.\n')

        try:
            os.utime(FULLGATHER_FILE, (start_time, start_time))
        except Exception, e:
            sys.stderr.write('WARNING: Full Gather run data update failed. %s\n' % str(e))
            log.write("Gather Failed. WARNING: Full Gather run data update failed.")

    print "Cleaning up temporary data...",
    if clean_tmp_dir(TMP_SUPPORT_DIR) == 0:
        print "done."

    verbose("\nCleaning up core/dumps")

    log.join()
    sys.exit(exit_status)


#  ########################### end main ###########################################
def osw_fix(error):
    # Make compatible with os.W*, since the callers all expect that.
    if error > 0:               # Exited without a signal
        return error << 8
    else:                       # Exited because of a signal
        return 0 - error


def get_popen(cmd, include_stderr=True, stdin=None):
    if include_stderr:
        stderr_pipe = subprocess.STDOUT
    else:
        stderr_pipe = subprocess.PIPE

    try:
        return subprocess.Popen(cmd, stdin=stdin, stderr=stderr_pipe,
                                stdout=subprocess.PIPE, close_fds=True,
                                shell=True)
    except OSError:
        print "While running", cmd
        raise


def get_popen_output(p, raw, strip=True):
    if raw:
        out = p.stdout.read()
    else:
        out = p.stdout.readlines()

    # Need to restart on EINTR.
    while True:
        try:
            error = p.wait()
            break
        except EnvironmentError, (error, strerror):
            if error == errno.EINTR:
                continue
            else:
                raise
    error = osw_fix(error)
    if strip and not raw:
        for i in range(len(out)):
            out[i] = out[i].rstrip()
    return (error, out)


# get_cmd_output
def get_cmd_output(cmd, include_stderr=True, raw=False, strip=True):
    '''
    Returns the exit status and output of the given command as a tuple.

    If raw evaluates to True, the output is returned unprocessed
    as a single string, otherwise it's returned as a list of rstrip()'d
    strings.

    If include_stderr evaluates to True, both stdout and stderr are
    included in the output, otherwise only stdout is included. In
    both cases, stderr is captured and not sent to the console.

    This function also has an advantage over os.system() in that

    it allows you to still catch KeyboardInterrupt exceptions. In detail:
    - If ^C is pressed during an os.system() call, the process being
      executed will be terminated, but no KeyboardInterrupt exception will
      be raised. Thus your script will continue executing as normal.
    - If ^C is pressed during a get_cmd_output() call, the process being
      executed will be terminated *and* a KeyboardInterrupt exception
      will be raised. Thus you can terminate your application appropriately,
      which is probably what the user was interested in doing. Hot damn.
    '''
    p = get_popen(cmd, include_stderr)
    if p:
        return get_popen_output(p, raw, strip)
    else:
        return (None, None)


def saveCommandLine():
    try:
        mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        fd = os.open(SAVED_COMMAND_LINE, mode, 0666)
        os.write(fd, " ".join(sys.argv) + "\n")
        os.close(fd)
    except OSError:
        error("Failed saving command-line output")


def savePackageInfo(pkginfo, fname):
    # this saves to the package information about the package
    contents = []
    if options.no_exempt_logs:
        contents.append('none')
    else:
        contents.append('full')

    for group in options.group:
        contents.append("group:%s" % group)

    revision = re.findall(r"\d+", REVISION)[0]

    # generate our xml
    pkg = etree.Element("package")
    pkg.attrib["version"] = "1"

    etree.SubElement(pkg, "command").text = " ".join(sys.argv)
    etree.SubElement(pkg, "contents").text = ", ".join(contents)
    etree.SubElement(pkg, "gather_date").text = str(pkginfo["gather_date"])
    etree.SubElement(pkg, "revision").text = revision

    logs = etree.Element("logs")
    etree.SubElement(logs, "last_full").text = str(pkginfo["last_full"])
    pkg.append(logs)

    f = open(fname, 'w')
    f.write(etree.tostring(pkg))
    f.close()


def waitForPid(pid):
    while True:
        pid, status = os.waitpid(pid, 0)
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            return 1


def waitForChildren(children):
    # NOTE using max(exit_results) could miss potential negative returns,
    # masked by (greater than) 0 success results.  This code will still
    # get max, ignoring all 0s, returning negatives if caught and "max".
    exit_results = [waitForPid(child) for child in children]
    exit_errors = filter(lambda x: x != 0, exit_results)
    error_count = len(exit_errors)
    exit_status = error_count and reduce(max, exit_errors) or 0
    return(exit_status, error_count, exit_results)


def makeDir(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path, 0775)
        except OSError, (errno, strerror):
            error("couldn't make %s directory: %s" % (path, os.strerror(errno)))


def getHostname():
    try:
        f = os.popen("/bin/hostname", "r")
        host_name = f.readline()
    except OSError, (errno, strerror):
        error("error running hostname: %s" % os.strerror(errno))
    f.close()

    host_name = host_name.strip()
    names = host_name.split('-')
    # this code does :
    # host_name      len(names) final names:
    # something      1          something
    # something-2    2          something
    # some-thing-2   3          some-thing
    # some-th-ing-2  4          some-th-ing
    if len(names) > 1:
        names.pop()
    stack_name = '-'.join(names)

    return stack_name, host_name


def makePkgName():
    if options.tarfile is not None:
        pkg_path_name = fixTarfileName(options.tarfile)
        if pkg_path_name is not None:
            return(pkg_path_name)

    time_string = time.strftime("%Y%m%d-%H%M%S")
    pkg_name = "RackHDLogs-%s-%s.tgz" % (stack.name, time_string)
    pkg_path_name = os.path.join(PKG_SUPPORT_DIR, pkg_name)

    return(pkg_path_name)


def makeDirs(dirs):
    '''Returns count of nodes that failed mkdir command.'''
    for dir in dirs:
        makeDir(dir)
    return(0)


def listGroups():
    print "\nKnown groups (included with the --group option): \n"
    groups = GROUPS.keys()
    groups.sort()
    for g in groups:
        print "  %s" % g
    print


def listUtils():
    print
    print "Known utilities (included with the -i option): \n"
    utils = UTILITIES.keys()
    utils.sort()
    for u in utils:
        if u not in EXEMPT:
            print "  %s" % u
    print


# this routine is simply here to print the warning message, and alert
# the user they munged the name.
# we skip removing the unknown name from the include array, since it won't
# hurt anything being in there (since the keys of the UTILITIES dict
# is what's searched).
def pruneUtils(requested):
    ulist = UTILITIES.keys()
    nlist = []
    for r in requested:
        if r not in ulist:
            print "WARNING: unknown utility (%s), ignored..." % r
        else:
            nlist.append(r)

    return(nlist)


# An internal correctness check to verify that everything in GROUPS and
# EXEMPT actually exists.
def validateUtils():
    util_errors = 0
    for (group, utils) in GROUPS.items():
        for util in utils:
            # if not UTILITIES.has_key(util):
            if util not in UTILITIES:
                util_errors += 1
                print "Unknown utility '%s' in group '%s'!" % (util, group)
    for util in EXEMPT:
        # if not UTILITIES.has_key(util):
        if util not in UTILITIES:
            print "Unknown utility '%s' in default group!" % util
    if util_errors:
        print "%d utility errors." % util_errors
        sys.exit(1)


# the logic: anything (valid) in the include list automatically means
# all other utilities are excluded (except for things in EXEMPT).
# (unless user specified '--nologs', which skips EXEMPT)
def buildRunUtils(ilist):
    if ilist is not None:
        list = pruneUtils(ilist)
    else:
        list = []
    if options.group_utils:
        list.extend(options.group_utils)
    if options.no_exempt_logs is False:
        list.extend(EXEMPT)
    return(list)


# Given a user-supplied tarfile, fix it to ensure:
# o If full path specified, use that path
# o If no full path given, use original PKG_SUPPORT_DIR path
# o Check extension: if usual tarfile extension, make sure we
#   don't "double up" with additional .tgz; otherwise keep intact.
# o Also check for special case '/' (root) specified
# Returns None for any problems (such as '/' case)
def fixTarfileName(tarfile):
    tarfile = os.path.normpath(tarfile.strip())
    # Note this verifies we were not given only '/'
    if len(tarfile) and not (tarfile[0] == '/' and len(tarfile) == 1):
        # Is it a full path or not? If not, supply default path.
        if tarfile[0] != '/':
            tarfile = PKG_SUPPORT_DIR + tarfile
        # Does it have an extension already?
        root, ext = os.path.splitext(tarfile)
        if ext in ['.tar', '.tgz']:
            tarfile = root
        elif ext in ['.gz']:
            root2, ext2 = os.path.splitext(root)
            if ext2 in ['.tar']:
                tarfile = root2
            else:
                tarfile = root
        else:
            # Note we'll just keep original extensions...
            pass
        tarfile = tarfile + ".tgz"
        return(tarfile)
    else:
        return(None)


def getPathFile(pathfile):
    # NOTE we need this rstrip mod for reliable dirname/basename!
    x = pathfile.rstrip('/')
    return(os.path.dirname(x), os.path.basename(x))


def getUtilityGatherCmd(name, path, base):
    # Avoid gathering duplicate data from all the nodes.
    # If path starts with /ifs, than gather data from only one node (local node)
    # e.g. path=/ifs/data or path=/ifs
    c = ('tar', "cd %s" % (path), "%s.tar %s" % (name, base))
    return(c)


# 'cmd' better be executable - either fullpath or in PATH
def getUtilityExecuteCmd(name, cmd, args):
    c = ('exe', "%s %s" % (cmd, args), "%s" % (name))
    return(c)


def makeUniqueDictKeyName(name, dict):
    new_name, count = name, 0
    while new_name in dict.keys():
        count += 1
        new_name = '%s-%d' % (name, count)
    return new_name


def verbose(str):
    if options.verbose:
        print >> sys.stdout, str


def error(str):
    print >> sys.stderr, PROGNAME + ':', str
    sys.exit(1)


def clean_tmp_dir(dir=TMP_SUPPORT_DIR):
    '''Function cleans up all temporary data on all nodes.  Returns the number
        of failures returned from executing rm.'''
    error_count = 0
    cmd_args = ["/bin/rm", "-rf", dir]
    cmd = " ".join(cmd_args)
    (exit, output) = get_cmd_output(cmd)
    if exit:
        error_count += 1
        print "\nERROR cleaning up %s, output follows:\n%s" % (dir, "\n".join(output))
    if error_count:
        print "You may wish to delete these files manually."
    return error_count


class MyLock(object):
    """class to handle .lock files
        """
    def __init__(self, path=GATHER_STATUS_LOCK, verbose=False):
        self.lockFD = ''
        self.lockfile = path
        self.pid = os.getpid()
        self.verbose = verbose

    def isPidRunning(self, pid):
        """checks if a given isi_gather_info is an active process"""
        cmd = """ps -o command= -p %d """
        try:
            (exit, output) = get_cmd_output(cmd % pid)
            if exit:
                return False
            if output and len(output):
                # if we get an output, it'll be just one element -> pid
                return 'isi_gather_info' in output[0]
            return False
        except:
            return False

    def _readlock(self):
        """reads the contents of a lock file. ie pid of the owner"""
        try:
            self.lockFD = os.open(self.lockfile, os.O_RDONLY)
            pid = os.read(self.lockFD, 100)
            os.close(self.lockFD)
            if pid != '':
                pid = int(pid)
            else:
                pid = 10**8
            return pid
        except:
            return False

    def _lock(self):
        """helper to lock()"""
        try:
            self.lockFD = os.open(self.lockfile, os.O_EXCL | os.O_CREAT | os.O_RDWR, 0400)
            os.write(self.lockFD, str(self.pid))
            os.close(self.lockFD)
            return True
        except OSError, e:
            if e.errno == 17:   # file exists!
                return False
            return False
        except:                 # any others
            return False

    def ownlock(self):
        """do i own lock"""
        try:
            lock = self._readlock()
            if lock:
                return self.pid == lock
            return False
        except:
            return False

    def lock(self):
        """locks. writes own pid to lock file"""
        # print "Locking self"
        # is gather-status unlocked? try locking
        if not os.path.exists(self.lockfile):
            return self._lock()
        else:
            pid = self._readlock()
            # is gather-status.lock owner running? ie lock expired?
            if not self.isPidRunning(pid):
                # print "Unlocking gather-status"
                self.unlock()
                return self._lock()
            else:
                print "%s is currently locked. Status Updates will not be written to file." % (self.lockfile)
        return False

    def unlock(self):
        """ unlocks lockfile """
        if os.path.exists(self.lockfile):
            print "Gather-status unlocked"
            try:
                os.remove(self.lockfile)
            except Exception:
                print "Error unlocking lockfile"
                return False
            return True
        else:
            print ("Gather-status lock does not exit")
            return False


class Logger(threading.Thread):
    """runs logging to file as a thread. timestamps the log file every
        self.updateInterval seconds. also allows async writes, as used
        to update program status.
    """
    def __init__(self, name="Logger", filename=GATHER_STATUS_PATH):
        self._stopevent = threading.Event()
        self.updateInterval = 3
        self.lastLogTime = 0
        self.filename = filename
        self.disable = False
        self.flock = MyLock()

        self.flock.owner = self.flock.lock()
        if self.flock.owner:
            try:
                self.fileFD = open(self.filename, 'w')
            except IOError:
                print "Could not open gather-status file. "
                self.disable = True
        else:
            self.disable = True
        threading.Thread.__init__(self, name=name)
        self.start()

    def run(self):
        """timestamps the file as long as the thread is active"""
        while (not self._stopevent.isSet()) and (not self.disable):
            self.write()
            time.sleep(self.updateInterval)

    def write(self, msg="", priority=False):
        """priority write. update with msg"""
        if (not self._stopevent.isSet()) and (not self.disable):
            try:
                self.lastLogTime = time.time()
                timestamp = "[%s] " % time.strftime("%Y-%m-%d %H:%M:%S")
                self.fileFD.writelines(timestamp + msg + '\n')
                self.fileFD.flush()
            except IOError:
                # this is to escape any errors generated by a closed terminal
                self.join(None)
                pass

    def join(self, timeout=None):
        self._stopevent.set()
        if self.flock.owner:
            try:
                self.fileFD.close()
                self.flock.unlock()
                threading.Thread.join(self, timeout)
            except Exception:
                print "Error unlocking gather log"
                pass


def get_options():
    global stack, options, log, re_upload

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hvlu:p:x:t:T:',
                                   ['help', 'version', 'list', 'user=', 'password=',
                                    'tarfile=', 'temp=', 'nologs', 'debug',
                                    'verbose', 'varlog_all', 'varlog_recent',
                                    'no-config', 'group=', 'noconfig', 'tardir='])

        for o, a in opts:
            if o in ['-h', '--help']:
                usage(0)
            elif o in ['-v', '--version']:
                version()
            elif o in ['-l', '--list']:
                listUtils()
                listGroups()
                sys.exit(0)
            elif o in ['--noconfig']:
                pass     # nothing to do here; handled above
            elif o in ['-u', '--user']:
                stack.user = a
            elif o in ['-p', '--password']:
                stack.password = a
            elif o in ['-x']:
                for each in a.split(', '):
                    try:
                        EXEMPT.remove(each)
                    except ValueError, e:
                        error("Utility %s does not exist to be excluded." % (each))
            elif o in ['-t', '--tarfile']:
                options.tarfile = a
            elif o in ['--tardir']:
                # this is a lot like -T, except -T still creates a 'pkg'
                # directory underneath the specified directory, which is
                # not always desirable.  I'd replace -T but I have no
                # idea if its being used.
                if not a.startswith('/'):
                    print "Tar directory %s invalid; it must begin with /"
                    sys.exit(1)
                options.tardir = a
            elif o in ['-T', '--temp']:
                options.tempdir = a.lstrip()
            elif o in ['--nologs']:
                options.no_exempt_logs = True
            elif o in ['--debug']:
                options.debug = True
            elif o in ['--verbose']:
                options.verbose = True
            elif o in ['--varlog_all']:
                # This is the default
                EXEMPT[0] = 'varlog_all'
            elif o in ['--varlog_recent']:
                EXEMPT[0] = 'varlog_recent'
            elif o in ['--group']:
                try:
                    options.group_utils.extend(GROUPS[a])
                    options.group.append(a)
                except KeyError, e:
                    print "Invalid group specified: %s" % a
                    listGroups()
                    sys.exit(1)
            else:
                print "Unknown argument: %s" % o
                usage(1)

    except getopt.GetoptError, e:
        error(str(e.msg))


def usage(exitCode):
    sys.stderr.write('''
Usage: %s [OPTION]...

Options:
  -h                  Print this message and exit.
  -v                  Print version info and exit.
  -u USER             Login as USER instead of default onrack.
  -p PASSWORD         Use PASSWORD.
  -t TARFILE          Save all results to TARFILE instead of default tar file.
  -T TEMPDIR          Save all results to TEMPDIR instead of default dir.
  --tardir <dir>      Place the final package directly into <dir>.

  Default temporary directory is %s
  (change with -T)

''' % (PROGNAME, VAR_SUPPORT_DIR))
    sys.exit(exitCode)


def version():
    print '%s version: %s' % (PROGNAME, REVISION)
    sys.exit(0)


if __name__ == '__main__':
    main()
