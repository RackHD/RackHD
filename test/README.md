# Running Integration Tests


## setup

    virtualenv .venv
    sudo pip install -r requirements.txt
    
    echo "deb https://dl.bintray.com/rackhd/debian trusty main" | sudo tee -a /etc/apt/sources.list.d/rackhd-trusty.list
    sudo apt-get update
    sudo apt-get install -y --force-yes python-on-http

## running the tests

run Vagrant environment

    cd ../example
    vagrant up
    vagrant ssh dev -c "sudo nf start"
    cd ../test

run the tests

    python run.py

## optional settings

Log levels
    
    export RACKHD_TEST_LOGLVL=[CRITICAL|ERROR|WARNING|INFO|DEBUG]
    NOTE: CRITICAL < ERROR < WARNING < INFO < DEBUG    

API host/port 

    export RACKHD_HOST=[host ip]
    export RACKHD_PORT=[host port]

AMQP URL

    export RACKHD_AMQP_URL=[amqp://<url>:<port>]

To reset the default target BMC user/password 

    cd ~/RackHD/test/
    rm .passwd
    python run.py
    <enter BMC username and password>
    NOTE: only prompts for user/password when .passwd file is missing
