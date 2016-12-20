## RackHD/OnRack Deployment Scripts

These scripts are to be used to deploy RackHD or OnRack onto a test 'stack'.
A 'stack' is a full test bed configuration that has a minimum of one server and one node.
Stacks are defined in the 'stack_config.json' file in the config directory.
Deployments must be run from a third party Ubuntu Linux test host with network access to the stack.

A stack deployment can come in several 'flavors':
- esxi: a stack conforming to the 'OnRack Reference Configuration' (server is a VM under ESXi)
- linux: a stack where the server is running under bare Linux
- docker: a stack where the server is running the Docker implementation

## Requirements and Setup

Python 2.7x is required for all FIT tests.
ESXi installation requires 'ovftool'.

Load the virtual environment on the Linux test host:

    virtualenv .venv
    source .venv/bin/activate
    pip install -r requirements.txt


## Wrapper scripts

Scripts starting with 'run_' are wrapper scripts which are used to sequence deployment steps.
Python 'nosetests' runs tests in alpha order which can be difficult to ensure proper sequencing of scripts.
A wrapper script can run scripts in sequence by calling them from numbered methods.
The installation and test suites are run from wrapper scripts.

Example for running RackHD installation:

    python run_tests.py -stack stack1 -test deploy/run_rackhd_installer.py


