#!/usr/bin/env bash


# Get ansible installed from PPA.
sudo add-apt-repository -y ppa:ansible/ansible
sudo apt-get update
sudo apt-get install -y ansible

# make the shortcut.
sudo cp /vagrant/ansible/rackhd-ansible.bash /usr/bin/rackhd-ansible

# Run the playbook
/usr/bin/rackhd-ansible
