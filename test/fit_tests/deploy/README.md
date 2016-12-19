## RackHD Deployment Scripts

These scripts are to be used to deploy RackHD onto a test 'stack'.
A 'stack' is a full test bed configuration that has a minimum of one server and one node.
Stacks are defined in the 'stack_config.json' file in the config directory.
Deployments must be run from a third party Ubuntu Linux test host with network access to the stack and access to Internet.

A stack deployment must be declared with a 'type' specified in the 'stack_config.json' file:
- vagrant: a stack conforming to the 'Vagrant' configuration running VirtualBox and Vagrant (default)
- esxi: a stack conforming to the ESXi Lab configuration where server is a VM under ESXi (Corsair Lab)
- linux: a stack where the server is running under bare Linux
- docker: a stack where the server is running the Docker implementation

## Requirements and Setup

Python 2.7x is required for all FIT tests.
ESXi installation requires 'ovftool'.
Vagrant installation requires 'VirtualBox' and 'Vagrant'.

Load the virtual environment on the Linux test host:

    virtualenv .venv
    source .venv/bin/activate
    pip install -r requirements.txt


## Jenkins Test Wrappers

Scripts starting with 'run_' are wrapper scripts which are typically used for Jenkins test automation.
These scripts are also handy for running installation or test manually.
Python 'nosetests' runs test scripts by default in alpha order which can be a problem when sequencing is required.
A wrapper script can run other scripts in sequence by calling them from numbered methods.

Example for running RackHD installation in a vagrant environment:

    python run_tests.py -stack vagrant -test deploy/run_vagrant_installer.py
