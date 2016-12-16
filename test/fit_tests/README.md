# FIT Test Overview

The FIT test suite is an open-source testing harness for RackHD and OnRack software.
RackHD (https://github.com/RackHD) is the open-sourced Hardware Management and Orchestration
software developed by EMC for datacenter administration.

FIT stands for Functional Integration Tests and is intended for Continuous Integration testing
as well as standalone testing. It was originally developed by the EMC OnRack test group to provide
the RackHD community a flexible test and deployment toolset that will work in a variety of
valid configurations and environments.

FIT is written in Python 2.7 'unittest' and uses Nose (nosetests) as the test runner.

# Running FIT

## Requirements and Setup

FIT tests are intended to be run on Ubuntu 14+ Linux.
Test harness may be run on appliance host (localhost), or third party machine.
Deployment scripts must be run under third party Ubuntu Linux host.
Tests require the following virtual environment commands be executed:

    virtualenv .venv
    source .venv/bin/activate
    pip install -r requirements.txt


## Directory Organization

The FIT test framework is under RackHD/test/fit_tests.

- 'tests' is the test 'harness'
- 'common' contains any common library functions
- 'deploy' contains deployment and installation scripts
- 'templates' contains script templates for making new tests
- 'util' contains non-test utilities

## Configuration

Local runtime parameters are set from the 'config/global_config.json' file.
Stack definitions are set from the 'config/stack_config.json' file.
An alternate configuration directory can be selected using the -config argument.
More details in config/README.md.

## Running the tests

All FIT tests can be run from the wrapper 'run_tests.py':

    usage: run_tests.py [-h] [-test TEST] [-config CONFIG] [-group GROUP]
                        [-stack STACK] [-ora ORA] [-version VERSION] [-xunit]
                        [-numvms NUMVMS] [-list] [-sku SKU]
                        [-obmmac OBMMAC | -nodeid NODEID] [-http | -https]
                        [-v V]

    Command Help

    optional arguments:
      -h, --help          show this help message and exit
      -test TEST          test to execute, default: tests/
      -config CONFIG      config file location, default: fit_tests/config
      -group GROUP        test group to execute: 'smoke', 'regression',
                          'extended', default: 'all'
      -stack STACK        stack label (test bed), overrides -ora
      -ora ORA            OnRack/RackHD appliance IP address or hostname, default:
                          localhost
      -version VERSION    OnRack package install version, example:onrack-
                          release-0.3.0, default: onrack-devel
      -template TEMPLATE  path or URL link to OVA template or OnRack OVA, default
                          from global_config.json
      -xunit              generates xUnit XML report files
      -numvms NUMVMS      number of virtual machine for deployment on specified
                          stack
      -list               generates test list only
      -sku SKU            node SKU, example:Phoenix, default=all
      -obmmac OBMMAC      node OBM MAC address, example:00:1e:67:b1:d5:64
      -nodeid NODEID      node identifier string of a discovered node, example:
                          56ddcf9a8eff16614e79ec74
      -http               forces the tests to utilize the http API protocol
      -https              forces the tests to utilize the https API protocol
      -port PORT          API port number override, default from
                          global_config.json
      -v V                Verbosity level of console output, default=0, Built Ins:
                          0: No debug, 2: User script output, 4: rest calls and
                          status info, 6: other common calls (ipmi, ssh), 9: all
                          the rest

This example will run the RackHD installer onto stack 1 via the wrapper script:

    python run_tests.py -stack 1 -test deploy/run_rackhd_installer.py


The -stack or -ora argument can be omitted when running on the server or appliance. The test defaults to localhost:8080 for API calls.

This example will run the smoke test from the appliance node or the default Vagrant test bed:

    python run_tests.py -test tests -group smoke


Alternatively tests can be run directly from nose. Runtime parameters such as ORA address must be set in the environment.

The following example will run all the entire test harness from a third party machine to ORA at 192.168.1.1:

    export ORA=192.168.1.1
    nosetests -s tests


## Running individual tests

Individual test scripts or tests may be executed using the following 'Nose' addressing scheme:

    test_script_path:classname.testname


For example, to run the test 'test_rackhd11_api_catalogs' in script 'tests/rackhd11/test_rackhd11_api_catalogs.py' on stack 1:

    python run_tests.py -stack 11 -test tests/rackhd11/test_rackhd11_api_catalogs.py:rackhd11_api_catalogs.test_api_11_catalogs


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
    cd RackHD/test/fit_tests
    vagrant up

This will load a virtual RackHD server and one virtual Quanta D51 node into VirtualBox.

Use the following commands to initialize the server and run a Smoke Test:

    vagrant ssh dev
    sudo bash
    source .venv/bin/activate
    cd fit_tests/test/fit_tests
    python run_tests.py -stack vagrant -test deploy/rackhd_stack_init.py -v 4
    python run_tests.py -test tests -group smoke

(On Windows, use Putty to log into the server using IP 127.0.0.1, port 2222, and credentials vagrant/vagrant)

Note that any previously installed RackHD Vagrant boxes will prevent a new instance from running.
Please remove any old RackHD VMs prior to executing this routine.

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

