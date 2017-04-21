# Save Logs
This utility provides the ability to gather log files and other useful information from a designated RackHD server and return it to the user.

## save_logs.py
Script which takes command line inputs and information from the optional configuration file to gather and return log data in the form of a tarball (tgz).  By default, it will extract the tarball in the deginated output directory.
It requires rackhd_gather_info.py and extract_logs.py to run.  

### save_logs_config.json
Optional configuration file for save_logs.py in json format.  This file allows defaulting certain parameters.

Supported fields are: username, password, webserver, log_directory_path, and ip. See the template confile for an example. 

## Usage:
```
save_logs.py  
usage: save_logs.py [-h] [-v] [-ip IP] [-port PORT] [-user USER] [-pwd PWD]
                    [-no_extract] [-log_path LOG_PATH]
                    [-target_dir TARGET_DIR]

  Command Help

  optional arguments:
    -h, --help            show this help message and exit
    -v                    Turn on verbose mode
    -ip IP                Appliance IP address or hostname
    -port PORT            Optional port argument for scp/ssh
    -user USER            Appliance username
    -pwd PWD              Appliance password
    -no_extract           Do not extract the tarball, default to extract
    -log_path LOG_PATH    Logging Directory Path
    -target_dir TARGET_DIR
                          Target directory name to store logs
```

### Usage examples:
Basic usage:
```
python save_logs.py -ip 1.2.3.4 -user name -pwd pass -target_dir mylogs
```
Without a config file present, it will save to current working dirctory path and prompt for target dir.
```
python save_logs.py -ip 1.2.3.4 -user name -pwd pass
```
With a config file present which contains ip, username, and password fields filled in:
```
python save_logs.py
```
With a config file present and using command line override for ip and logpath:
```
python save_logs -ip stack6-ora.admin -log_path /emc/higgib3/logfiles
```

## extract_logs.py  
Script to unfurl the save_logs tarball into the current or desginated directory.

```
extract_logs.py  
usage: extract_logs.py [-h] [-pkg PKG] [-dir DIR] [-output_dir OUTPUT_DIR]

  Command Help

  optional arguments:
    -h, --help            show this help message and exit
    -pkg PKG              .tgz file to be extracted
    -dir DIR              directory .tgz file is located and default extraction
                          location
    -output_dir OUTPUT_DIR
                          optional directory to extract to, defaults to tgz
                          location
```
Extract to directory holding the file
```
python extract_logs.py -dir logs -pkg RackHDLogs-ora-20161118-104809.tgz
```

Extract to different directory
```
python extract_logs.py -dir logs -pkg RackHDLogs-ora-20161118-104809.tgz -output_dir /emc/higgib3/scripts
```

## rackhd_gather_info.py
The main script used by save_logs.py to gather data from the RackHD stack(server). The script runs locally on the RackHD stack(server).

This script is based upon an EMC Isilon utility and not all functionallity listed within it is currently used, but was left in for future improvements. The base default functionality is all that is needed for save_logs for RackHD.


## Sample Run Output:
Save logs and do not extract:
```
python save_logs.py -ip stack10-ora.admin -user onrack -pwd onrack -no_extract -target_dir eh-demo1

save_logs: Using configuration from "save_logs_conf.json".
Saving logs in directory path: /mnt/cilogserver/bug_logs/
This utility will attempt to gather log files and data from your appliance for debugging.
Pushing gather script to stack....
Running gather logs script, please wait.....
Saved logs on stack in  /tmp/rackhd/pkg/RackHDLogs-ora-20161205-105524.tgz
Copying from stack....

Log directory: /mnt/cilogserver/bug_logs/eh-demo1
Webserver: https://web.hwimo.lab.emc.com/qa/log/bug_logs/eh-demo1
```
Save logs and extract:
```
python save_logs.py -ip stack10-ora.admin -target_dir eh-demo10 -user onrack -pwd onrack

save_logs: No config file found
Saving logs in current directory: /mydir/rackhd/loggather/test/tools/save-logs
This utility will attempt to gather log files and data from your appliance for debugging.
Pushing gather script to stack....
Running gather logs script, please wait.....
Saved logs on stack in  /tmp/rackhd/pkg/RackHDLogs-ora-20170418-084932.tgz
Copying from stack....
Extracting tarball.....

Log directory: /mydir/rackhd/loggather/test/tools/save-logs/eh-demo10
```

# Running in a virtual environment.
It may be necessary to run in a vitural environment if not all imported packages are available from your system.
Here is an example of this if pexpect missing.
```
virtualenv myenv
source myenv/bin/activate
  pip list
  pip install pexpect

  python save_logs.py [args]
  python extract_logs.py [args]

deactivate
```

