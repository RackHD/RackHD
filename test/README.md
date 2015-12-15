# Running Integration Tests


## setup

    virtualenv .venv
    sudo pip install -r requirements.txt

## running the tests

run Vagrant environment

    cd ../example
    vagrant up
    vagrant ssh dev -c "sudo nf start"
    cd ../test

run the tests

    python run.py
