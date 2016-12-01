#!/bin/bash
set -e


#Load library func
source get_nic_name_by_index.sh

########################################
# Main
#######################################
Control_NIC=$(get_secondary_nic_name)

# Update the /etc/default/isc-dhcp-server, let DHCP Service running on Control Port.
line="INTERFACES=\"$Control_NIC\""
echo $line >> /etc/default/isc-dhcp-server

echo "[Info] The Control NIC is ${Control_NIC}. Added it into /etc/default/isc-dhcp-server"
