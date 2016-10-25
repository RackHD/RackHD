# Copyright 2016, EMC, Inc.

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    config.vm.define "default" do |target|
        target.vm.box = "comiq/dockerbox"
        target.vm.box_version = "1.12.1.1"

        target.vm.provider "virtualbox" do |v|
            v.memory = 4096
            v.cpus = 4
            v.customize ["modifyvm", :id,
              "--nictype1", "virtio",
              "--nicpromisc2", "allow-all"
            ]
        end

        target.vm.network "private_network", ip: "172.31.128.1", virtualbox__intnet: "closednet"

        target.vm.network "forwarded_port", guest: 4243, host: 4243, id: "Docker Remote API"

        target.vm.network "forwarded_port", guest: 27017, host: 27017, id: "Mongo DB"
        target.vm.network "forwarded_port", guest: 15672, host: 15672, id: "RabbitMQ Management"
        target.vm.network "forwarded_port", guest: 5672, host: 5672, id: "RabbitMQ AMQP"

        target.vm.network "forwarded_port", guest: 9080, host: 9080, id: "RackHD Southbound API"
        target.vm.network "forwarded_port", guest: 9090, host: 9090, id: "RackHD Northbound API"
        target.vm.network "forwarded_port", guest: 9100, host: 9100, id: "RackHD WebSocket Server"

        target.vm.network "forwarded_port", guest: 5601, host: 5601, id: "Kibana UI"
        target.vm.network "forwarded_port", guest: 9200, host: 9200, id: "Elasticsearch REST API"
        target.vm.network "forwarded_port", guest: 9300, host: 9300, id: "Elasticsearch Native"

        target.vm.synced_folder "..", "/RackHD"
        target.vm.synced_folder '.', '/vagrant', disabled: true

        target.vm.provision :shell, inline: <<-SHELL
          set -e # fail on error
          set -x # debug commands
          cp /lib/systemd/system/docker.service /docker.service.bak
          sed -e \
            's/ExecStart=.*/ExecStart=\\/usr\\/bin\\/docker daemon -H fd:\\/\\/ -H tcp:\\/\\/0.0.0.0:4243/g' \
            /lib/systemd/system/docker.service > /docker.service.sed
          cp /docker.service.sed /lib/systemd/system/docker.service
          systemctl daemon-reload
          service docker restart
        SHELL
    end
end
