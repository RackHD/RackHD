#!/bin/bash

# Setup policy for rabbitmq mirrored queue cluster

docker exec -t -i docker_rabbit_1 rabbitmqctl set_policy on-all "^on." '{"ha-mode":"all"}'
docker exec -t -i docker_rabbit_1 rabbitmqctl set_policy sku-all "^sku\." '{"ha-mode":"all"}'
docker exec -t -i docker_rabbit_1 rabbitmqctl set_policy graph-all "^graph\." '{"ha-mode":"all"}'
docker exec -t -i docker_rabbit_1 rabbitmqctl set_policy waterline "waterline" '{"ha-mode":"all"}'
