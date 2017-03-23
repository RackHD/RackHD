#!/bin/bash

echo "Setup policy for rabbitmq mirored queue cluster"

policies=("on-all ^on\. {\"ha-mode\":\"all\"}" "sku-all ^sku\. {\"ha-mode\":\"all\"}"  "graph-all ^graph\. {\"ha-mode\":\"all\"}" "waterline waterline {\"ha-mode\":\"all\"}")

for i in "${policies[@]}"

do

    docker exec -t -i docker_rabbit_1 rabbitmqctl set_policy $i

done

