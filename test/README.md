# FIT-based Test Overview

The FIT test suite is an open-source testing harness for RackHD software.
RackHD (https://github.com/RackHD) is the open-sourced Hardware Management and Orchestration
software developed by EMC for datacenter administration.

FIT stands for Functional Integration Tests and is intended for Continuous Integration testing
as well as standalone testing. It was originally developed by the EMC RackHD test group to provide
the RackHD community a flexible test and deployment toolset that will work in a variety of
valid configurations and environments.

FIT is written in Python 2.7 'unittest' and uses Nose (nosetests) as the test runner.

# Running FIT

## Requirements and Setup

FIT tests are intended to be run on Ubuntu 14+ Linux.
Test harness may be run on appliance host (localhost), or third party machine.
Deployment scripts must be run under third party Ubuntu Linux host.
Tests require the following virtual environment commands be executed:

    ./mkenv.sh
    source myenv_fit


## Directory Organization

The FIT test framework is under RackHD/test

- 'tests' is the test 'harness'
- 'common' contains any common library functions
- 'deploy' contains deployment and installation scripts
- 'stream-monitor' contains a nose-plugin to help with monitoring various
   streams (logs/amqp) and providing services around that
- 'templates' contains script templates for making new tests
- 'util' contains non-test utilities

## Configuration

Default configuration file values can be found in the following files:
* 'config/rackhd_default.json'
* 'config/credentials_default.json'
* 'config/install_default.json'

Stack definitions are set from the 'config/stack_config.json' file.
An alternate configuration directory can be selected using the -config argument.
More details in config/README.md.

## Running the tests

All FIT tests can be run from the wrapper 'run_tests.py':

### --help output
        usage: run_tests.py [-h] [-test TEST] [-config CONFIG] [-group GROUP]
                            [-stack STACK] [-rackhd_host RACKHD_HOST]
                            [-template TEMPLATE] [-xunit] [-numvms NUMVMS] [-list]
                            [-sku SKU] [-obmmac OBMMAC | -nodeid NODEID]
                            [-http | -https] [-port PORT] [-v V] [-nose-help]

        Command Help

        optional arguments:
          -h, --help            show this help message and exit
          -test TEST            test to execute, default: tests/
          -config CONFIG        config file location, default: config
          -group GROUP          test group to execute: 'smoke', 'regression',
                                'extended', default: 'all'
          -stack STACK          stack label (test bed)
          -rackhd_host RACKHD_HOST
                                RackHD appliance IP address or hostname, default:
                                localhost
          -template TEMPLATE    path or URL link to OVA template or RackHD OVA
          -xunit                generates xUnit XML report files
          -numvms NUMVMS        number of virtual machines for deployment on specified
                                stack
          -list                 generates test list only
          -sku SKU              node SKU name, example: Quanta-T41, default=all
          -obmmac OBMMAC        node OBM MAC address, example:00:1e:67:b1:d5:64
          -nodeid NODEID        node identifier string of a discovered node, example:
                                56ddcf9a8eff16614e79ec74
          -http                 forces the tests to utilize the http API protocol
          -https                forces the tests to utilize the https API protocol
          -port PORT            API port number override, default from
                                install_config.json
          -v V                  Verbosity level of console and log output (see -nose-
                                help for more options), Built Ins: 0: Minimal logging,
                                1: Display ERROR and CRITICAL to console and to files,
                                3: Display INFO to console and to files, 4: (default)
                                Display INFO to console, and DEBUG to files, 5:
                                Display infra.run and test.run DEBUG to both, 6: Add
                                display of test.data (rest calls and status) DEBUG to
                                both, 7: Add display of infra.data (ipmi, ssh) DEBUG
                                to both, 9: Display infra.* and test.* at DEBUG_9 (max
                                output)
          -nose-help            display help from underlying nosetests command,
                                including additional log options


### Example that will run the RackHD installer onto stack 1 via the wrapper script:

    python run_tests.py -stack 1 -test deploy/run_rackhd_installer.py

### Example will run the smoke test from the appliance node or the default Vagrant test bed:

    python run_tests.py -test tests -group smoke

The -stack or -rackhd_host argument can be omitted when running on the server or appliance. The test defaults to localhost:8080 for API calls.


### Running individual tests

Individual test scripts or tests may be executed using the following 'Nose' addressing scheme:

    test_script_path:classname.testname


For example, to run the test 'test_rackhd11_api_catalogs' in script 'tests/rackhd11/test_rackhd11_api_catalogs.py' on stack 1:

    python run_tests.py -stack 1 -test tests/rackhd11/test_rackhd11_api_catalogs.py:rackhd11_api_catalogs.test_api_11_catalogs

### Example of rerunning a test based on a previous run's configuration:

When run_tests.py executes, a generated configuration will be created in the
config/generated directory.  The name will appear in the run_test.py output.

A previously generated configuration can be used again for a run_tests.py
invocation by setting the environment variable FIT_CONFIG.

This shows the config being generated:

     python run_tests.py -stack 1 -test deploy/run_rackhd_installer.py
     *** Created config file: config/generated/fit-config-20170118-160319
     *** Using config file: config/generated/fit-config-20170118-160319

This shows re-using the generated config:

     export FIT_CONFIG=config/generated/fit-config-20170118-160319
     python run_tests.py

## Running FIT tests on Vagrant RackHD

The RackHD 'Vagrant' configuration is a convenient simulated hardware environment with one management server and one node running as VMs.
It can be run on a Windows or Ubuntu Linux workstation for testing and development.

Install Git, Oracle VirtualBox. and HashiCorp Vagrant from the following links onto a Windows or Linux host machine or workstation

    https://git-scm.com/downloads
    https://www.virtualbox.org/wiki/Downloads (version 5.1 or greater)
    https://www.vagrantup.com/downloads.html (version 1.8.5 or greater)

Open a shell or command prompt on host.

Run the following commands at the command prompt:

    git clone https://github.com/RackHD/RackHD
    cd RackHD/test
    vagrant up

This will load a virtual RackHD server and one virtual Quanta D51 node into VirtualBox.

Use the following commands to initialize the server and run a Smoke Test:

    vagrant ssh dev
    sudo bash
    cd fit_tests/test
    ./mkenv.sh vagrant
    source myenv_vagrant
    python run_tests.py -stack vagrant -test deploy/rackhd_stack_init.py -v 4
    python run_tests.py -test tests -group smoke

(On Windows, use Putty to log into the server using IP 127.0.0.1, port 2222, and credentials vagrant/vagrant)

Note that any previously installed RackHD Vagrant boxes will prevent a new instance from running.
Please remove any old RackHD VMs prior to executing this routine.

## Hints and background for logging/debuging tests

Please read 'stream_monitor/flogging/README.md' for information on the logging system.
That file also contains a set of common "if you want this to happen, type this" at the top of the file and how
the existing '-v' shortcut option maps to the loggers.

## Test conventions

- Tests should be written using Python 'unittest' classes and methods.
- Tests should utilize common library functions for API and appliance shell access.
- Tests should leave the DUT(Device Under Test) in the same state that it was found. For example, if the test creates a node, then delete it.
The setUp and tearDown methods are useful ways to setup and clean out test-specific conditions.
- Tests should have meaningful names that relate to its function.
- If tests need to be run in a sequence, use numbered class and method names 'test01'. 'test02', etc.
- If scripts need to run in a sequence, use a wrapper script and number the method names.
- Tests that need specific conditions should be run in a single script and utilize 'setUp' and 'tearDown' methods.
- Tests should not have any direct references to IP addresses or hostnames. Use GLOBAL_CONFIG or STACK_CONFIG for hardware or resource references.


# CIT-based Test Overview

## Setup

    NOTE: virtualenv version used 1.11.4 (Ubuntu). Using virtualenv is optional here but suggested.

    virtualenv .venv
    source .venv/bin/activate
    sudo pip install -r requirements.txt

## Running the tests

Run Vagrant environment

    cd ../example
    vagrant up
    vagrant ssh dev -c "sudo pm2 start rackhd-pm2-config.yml"
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
