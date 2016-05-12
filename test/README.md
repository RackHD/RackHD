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

## Optional settings

Log levels
    
    NOTE: CRITICAL < ERROR < WARNING < INFO < DEBUG

    export RACKHD_TEST_LOGLVL=[CRITICAL|ERROR|WARNING|INFO|DEBUG default=WARNING]

API host/port 

    export RACKHD_HOST=[host ip default=localhost]
    export RACKHD_PORT=[host port default=9090]

AMQP URL

    export RACKHD_AMQP_URL=[amqp://<url>:<port> default=amqp://localhost:9091]

Specify test groups
    
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
