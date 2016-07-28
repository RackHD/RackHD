#!/usr/bin/env bash
sudo ansible-playbook -i /vagrant/ansible/inventory-vagrant.ini /opt/ansible/rackhd/rackhd_package.yml
