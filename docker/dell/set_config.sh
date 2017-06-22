#!/bin/bash
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/DEVICE-DISCOVERY/data --data-binary @- < config/device-discovery.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/virtualnetwork/data --data-binary @- < config/virtualnetwork.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/virtualidentity/data --data-binary @- < config/virtualidentity.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/gateway-zuul/data --data-binary @- < config/gateway.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/SWAGGER-AGGREGATOR/data --data-binary @- < config/swagger-aggregator.yml

