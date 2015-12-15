# Running Integration Tests


## setup

    virtualenv .venv
    pip install -r requirements.txt

## running the tests

run Vagrant environment

    cd ../example
    vagrant up
    vagrant ssh dev -c "sudo nf start"
    cd ../CI

run the tests

    python run.py
