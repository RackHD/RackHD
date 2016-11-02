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
    vagrant ssh dev -c "sudo pm2 start rackhd.yml"
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

## Configuration

    Default configuration options and their definitions are defined in config/config.ini.  
    Custom config.ini can be specified by using the --config command line parameter:

    python run.py --config=/home/user/config.ini

    
## HTTP proxy configuration:

For OS installer related tests, optional HTTP proxies for accessing remote OS image repositories can be defined, see the [RackHD Configuration howto](http://rackhd.readthedocs.io/en/latest/rackhd/configuration.html?highlight=httpProxies#rackhd-configuration)

## Specifying test groups
    
    To display the entire test plan and available test groups run:

    python run.py --show-plan

    Use the nosetest --group option to test a specific group:

    Run only v1.1 API related tests:
    python run.py --group=api-v1.1

    Run only v2.0 API related tests:
    python run.py --group=api-v2.0

    Run only Redfish 1.0 compliant API related tests:
    python run.py --group=api-redfish-1.0

## To reset the default target BMC user/password 

    NOTE: only prompts for user/password when .passwd file is missing

    cd ~/RackHD/test/
    rm .passwd
    python run.py
    <enter BMC username and password>

## Running footprint benchmark test

Footprint benchmark collects system data when running poller, node discovery and bootstrap.
Details can be found in WIKI page:
[proposal-footprint-benchmarks](https://github.com/RackHD/RackHD/wiki/proposal-footprint-benchmarks)
The benchmark data collection process can also start/stop independently without binding to any test case,
thus users can get the footprint info about any operations they carry out during this period of time.

###Precondition

The machine running RackHD can use apt-get to install packages, which means it must have accessible sources.list

In RackHD, compute nodes have been discovered, and pollers are running

No external AMQP queue with the name "graph.finished" is listening RackHD

Make sure the AMQP port in RackHD machine can be accessed by the test machine.
If you are not using Vagrant, you can tunnel the port by the following command in RackHD

    sudo socat -d -d TCP4-LISTEN:55672,reuseaddr,fork TCP4:localhost:5672

###Settings

Aside from Optional settings in the section above,
following parameters are also required at the first time user issuing the test,
and stored in .passwd

    localhost username and password: username and password that can run "apt-get install"
    in the machine running the test

###Running the tests

Run poller|discovery|bootstrap tests

    python benchmark.py --group=poller|discovery|bootstrap

Run all benchmark tests

    python benchmark.py

Start|Stop benchmark data collection

    python benchmark.py --start|stop

Get the directory of the latest log data

    python benchmark.py --getdir

###Getting result

Footprint report is in ~/benchmark/(timestamp)/(case)/report.

Report in html format can display its full function by

    chrome.exe --user-data-dir="C:/Chrome dev session" --allow-file-access-from-files

to open the browser and drag the summary.html to it.

Data summary and graph is shown by process and footprint matrix.

Data in different time and cases can be selected to compare with the current one.
