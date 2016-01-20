# Running Integration Tests


## Setup

    NOTE: virtualenv version used 1.11.4 (Ubuntu). Using virtualenv is optional here but suggested.

    virtualenv .venv
    sudo pip install -r requirements.txt
    
## Running the tests

Run Vagrant environment

    cd ../example
    vagrant up
    vagrant ssh dev -c "sudo nf start"
    cd ../test

Run the tests

    python run.py

## Optional settings

Log levels
    
    NOTE: CRITICAL < ERROR < WARNING < INFO < DEBUG

    export RACKHD_TEST_LOGLVL=[CRITICAL|ERROR|WARNING|INFO|DEBUG default=WARNING]

API host/port 

    export RACKHD_HOST=[host ip default=localhost]
    export RACKHD_PORT=[host port default=9090]

AMQP URL

    export RACKHD_AMQP_URL=[amqp://<url>:<port> default=amqp://localhost:9091]

To reset the default target BMC user/password 

    NOTE: only prompts for user/password when .passwd file is missing

    cd ~/RackHD/test/
    rm .passwd
    python run.py
    <enter BMC username and password>
