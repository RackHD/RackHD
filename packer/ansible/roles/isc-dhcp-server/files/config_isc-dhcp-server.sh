#!/bin/bash
set -e

############################################################
##     Why Duplication code below ?
##
## Below two functions come from packer/scripts/common/get_nic_name_by_index.sh
## becauce when packer execute ansible ,
## packer will copy the whole packer/ansible folder to VM's /tmp/packer-provisioner-ansible-local
## but the files outside packer/ansible do not exist in VM's filesystem.
## so ansible-playbook can't copy common/get_nic_name_by_index.sh because ansible can't find it anywhere.
## so we will have to duplicate below scripts here.
############################################################


##########################################################
# retrieve nic name via ```ip addr``` command, by given id
#
# param: index of nic(starting from 1)
#
# echo:  the nic name
#
# exception:  exit non-zero with echo error message
##########################################################
get_nic_name_by_index()
{
    #######################
    # this script is to obtain and echo the nic name (lo/eth0/eth1) by index(1/2/3) shown in ```ip addr```
    #
    #
    # ip addr will show:
    #
    #1: lo: <loopback,up,lower_up> mtu 65536 qdisc noqueue state unknown group default
    #.......
    #2: eth0: <broadcast,multicast,up,lower_up> mtu 1500 ...
    #.......
    #3: eth1: <broadcast,multicast,up,lower_up> mtu 1500 qdisc pf....
    #......
    #
    ########################
    id=$1
    if ! [[ "$id" =~ ^[0-9]+$ ]] || [[ "$id" -eq 0 ]]; then
        echo "[error]: invalid parameter passed to get_nic_name_by_index(): nic id=${id} should be number and be larger than 0.";
        exit 1
    fi

    tmp=$( ip addr|grep "^${id}:" | awk '{print $2}')

    # the output should be like "lo:", "eth1:", "br-123asdf23:" if this nic index exists
    if [[ "$tmp" == "" ]] || ! [[ $(echo $tmp|grep ":$") ]]
    then
        echo "[error]: invalid parameter passed to get_nic_name_by_index(): nic id=${id} not detected";
        exit 2
    fi
    name=${tmp/:/}  # remove the ":"
    echo $name
}

#################################
# retrieve secondary nic name(example :control port of rackhd), skipping the loopback dev(lo)
#
# echo:  the nic name
################################
get_secondary_nic_name()
{

    # by default, the control port index is 3. say: eth1/enp0s8/ens33...
    sec_nic_index=3;


    # if the index 1 is not loopback device, then eth0 may starts from index 1.
    nic1=$(get_nic_name_by_index 1)
    if [[ $nic1 != "lo" ]]; then
        sec_nic_index=$(expr $sec_nic_index - 1 )
    fi

    sec_nic=$(get_nic_name_by_index $sec_nic_index)

    echo $sec_nic
}


########################################
# Main
#######################################
Control_NIC=$(get_secondary_nic_name)

# Update the /etc/default/isc-dhcp-server, let DHCP Service running on Control Port.
line="INTERFACES=\"$Control_NIC\""
echo $line >> /etc/default/isc-dhcp-server

echo "[Info] The Control NIC is ${Control_NIC}. Added it into /etc/default/isc-dhcp-server"
