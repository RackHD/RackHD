# Running Integration Tests


## Setup

    NOTE: virtualenv version used 1.11.4 (Ubuntu). Using virtualenv is optional here but suggested.

    virtualenv .venv
    source .venv/bin/activate
    sudo pip install -r requirements.txt
    
## Running the tests

Run Vagrant environment

    cd ../example
    vagrant up
    vagrant ssh dev -c "sudo nf start"
    cd ../test

Run the tests

    Defaults to smoke-test group.

    python run.py

Run smoke tests

    Runs limited functional test set to validate basic functionality.

    python run.py --group=smoke-tests

Run regression tests

    Runs smoke-tests with an extended functional test set.

    python run.py --group=regression-tests

## Optional Environment Variables

Log levels
    
    NOTE: CRITICAL < ERROR < WARNING < INFO < DEBUG

    export RACKHD_TEST_LOGLVL=[CRITICAL|ERROR|WARNING|INFO|DEBUG default=WARNING]

API host/port 

    export RACKHD_HOST=[host ip default=localhost]
    export RACKHD_PORT=[host port default=9090]

AMQP URL

    export RACKHD_AMQP_URL=[amqp://<url>:<port> default=amqp://localhost:9091]

OS Installer locations

    Specify specific OS repository path:

    export RACKHD_CENTOS_REPO_PATH=[location to http mirror for all CentOS images]
    export RACKHD_ESXI_REPO_PATH=[location to http mirror for all ESXi images]
    export RACKHD_UBUNTU_REPO_PATH=[location to http mirror for all Ubuntu images]
    export RACKHD_SUSE_REPO_PATH=[location to http mirror for all SUSE images]

    Example: export RACKHD_CENTOS_REPO_PATH=http://ip:port/repo/centos

HTTP proxy configuration (optional):

To define HTTP proxies for accessing remote OS image repositories, see the [RackHD Configuration howto](http://rackhd.readthedocs.io/en/latest/rackhd/configuration.html?highlight=httpProxies#rackhd-configuration)

Specifying test groups
    
    To display the entire test plan and available test groups run:

    python run.py --show-plan

    Use the nosetest --group option to test a specific group:

    Run only v1.1 API related tests:
    python run.py --group=api-v1.1

    Run only v2.0 API related tests:
    python run.py --group=api-v2.0

    Run only Redfish 1.0 compliant API related tests:
    python run.py --group=api-redfish-1.0

To reset the default target BMC user/password 

    NOTE: only prompts for user/password when .passwd file is missing

    cd ~/RackHD/test/
    rm .passwd
    python run.py
    <enter BMC username and password>

## Running footprint benchmark test

Footprint benchmark collects system data when running poller, node discovery and bootstrap.
Details can be found in WIKI page:
[proposal-footprint-benchmarks](https://github.com/RackHD/RackHD/wiki/proposal-footprint-benchmarks)

###Precondition

In RackHD, compute nodes have been discovered, and pollers are running

No external AMQP queue with the name "graph.finished" is listening RackHD

Make sure the AMQP port in RackHD machine can be accessed by the test machine.
If you are not using Vagrant, you can tunnel the port by the following command in RackHD

    sudo socat -d -d TCP4-LISTEN:55672,reuseaddr,fork TCP4:localhost:5672

###Settings

Aside from Optional settings in the section above,
following parameters are also required at the first time user issuing the test,
and stored in .passwd

    localhost username and password: for the machine running the test
    RackHD ssh port, username and password

###Running the tests

Run poller tests

    python benchmark.py --group=poller

Run discovery tests

    python benchmark.py --group=discovery

Run bootstrap tests

    python benchmark.py --group=bootstrap

Run all benchmark tests

    python benchmark.py

###Getting result

Footprint report is in ~/benchmark/(timestamp)/(case)/report.

Report in html format can display its full function by

    chrome.exe --user-data-dir="C:/Chrome dev session" --allow-file-access-from-files

to open the browser and drag the summary.html to it.

Data summary and graph is shown by process and footprint matrix.

Data in different time and cases can be selected to compare with the current one.
