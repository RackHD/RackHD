######################
# Vagrant File Start #
######################

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

    # RackHD SERVER
    config.vm.define "dev_ansible" do |target|
        target.vm.box = "rackhd/rackhd-dev"
        target.vm.provider "virtualbox" do |v|
            v.memory = 4096
            v.cpus = 4
            v.customize ["modifyvm", :id, "--nicpromisc2", "allow-all", "--ioapic", "on"]
        end

        # NOTE: virtualbox shared folder syncing can be quite slow, but shared folders
        # can be configured as NFS mounts to the host instead.
        # To do so, append: `, type: "nfs"` to all of the target.vm.synced_folder commands
        # below, then on the host system, run `sudo nfsd start`.
        # Additionally, uncomment the below configuration:

        # For NFS mounts, a host only network is needed. Feel free to change the IP.
        # target.vm.network "private_network", ip: "192.168.50.4"

        # Sync optional local workspace directory to the vagrant instances src/ path.
        # REPO is optional when WORKSPACE is defined, used for synchronizing single RackHD repos
        # otherwise it assumes all service repos have been cloned and built under the WORKSPACE path.
        # NOTE: See further below for instructions on how to use an NFS mount for faster synced file performance
        if ENV['WORKSPACE']
          if ENV['REPO'] == "on-tasks"
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['REPO']}", "/home/vagrant/src/on-taskgraph/node_modules/on-tasks/"
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['REPO']}", "/home/vagrant/src/on-http/node_modules/on-tasks/"
          elsif ENV['REPO'] == "on-core"
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['REPO']}", "/home/vagrant/src/on-taskgraph/node_modules/on-core/"
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['REPO']}", "/home/vagrant/src/on-http/node_modules/on-core/"
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['REPO']}", "/home/vagrant/src/on-tftp/node_modules/on-core/"
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['REPO']}", "/home/vagrant/src/on-dhcp-proxy/node_modules/on-core/"
          end
          target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['REPO']}", "/home/vagrant/src/#{ENV['REPO']}"
          if ENV['CONFIG_DIR']
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['CONFIG_DIR']}", "/opt/onrack/etc/"
            target.vm.synced_folder "#{ENV['WORKSPACE']}/#{ENV['CONFIG_DIR']}", "/home/vagrant/opt/monorail/"
          end
        end

        # Create a public network, which generally matched to bridged network.
        # Bridged networks make the machine appear as another physical device on
        # your network.
        # target.vm.network :public_network

        # Specify optional interface to bridge when wanting to expose the instance to an
        # external network.  Useful for when discovering nodes externally.
        if ENV['BRIDGE_INTF']
           target.vm.network "public_network", ip: "172.31.128.1", bridge: "#{ENV['BRIDGE_INTF']}"
        else
           target.vm.network "private_network", ip: "172.31.128.1", virtualbox__intnet: "closednet"
        end
        target.vm.network "forwarded_port", guest: 8080, host: 9090
        target.vm.network "forwarded_port", guest: 5672, host: 9091
        target.vm.network "forwarded_port", guest: 9080, host: 9092
        target.vm.network "forwarded_port", guest: 8443, host: 9093

        # NOTE: virtualbox shared folder syncing can be quite slow, but shared folders
        # can be configured as NFS mounts to the host instead.
        # To do so, append: `, type: "nfs"` to all of the target.vm.synced_folder commands
        # below, then on the host system, run `sudo nfsd start`.
        # Additionally, uncomment the below configuration:
        #
        # For NFS mounts, a host only network is needed. Feel free to change the IP.
        # target.vm.network "private_network", ip: "192.168.50.4"

        # If true, then any SSH connections made will enable agent forwarding.
        # Default value: false
        target.ssh.forward_agent = true

        target.vm.provision "shell", inline: <<-SHELL
          sudo service isc-dhcp-server start
          #install ansible
          sudo su
          #sudo apt-get install -y software-properties-common
          #sudo apt-add-repository ppa:ansible/ansible
          #sudo apt-get update
          #sudo apt-get install -y ansible 
        
          #install RackHd with ansible
          sudo ansible-playbook /vagrant/install_rackhd_vagrant.yml  
          sudo pm2 start /home/vagrant/rackhd-pm2-config.yml         
        SHELL
    end

    # Virtual HW SERVER
    config.vm.define "quanta_d51" do |target|
        target.vm.box = "InfraSIM/quanta_d51"
        target.vm.provider "virtualbox" do |v|
            v.memory = 4096
            v.cpus = 4
            v.customize ["modifyvm", :id, "--nicpromisc2", "allow-all", "--ioapic", "on"]
        end
        #target.vm.network :public_network
        target.vm.network "private_network", virtualbox__intnet: "closednet", auto_config: false, nic_type: "82540EM"
        target.vm.provision "shell", inline: <<-SHELL
            sudo ifconfig eth1 up
            sleep 2
            sudo udhcpc -i br1
        SHELL
    end


end
