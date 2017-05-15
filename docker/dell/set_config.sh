#!/bin/bash

curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/virtualnetwork/data --data-binary @- < ../config/VIRTUALNETWORK-test.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/virtualidentity/data --data-binary @- < ../config/VIRTUALIDENTITY-test.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/gateway-zuul/data --data-binary @- < ../config/GATEWAY-test.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/SMI-GATEWAY/data --data-binary @- < ../config/GATEWAY-services.yml
curl -XPUT -H "Content-Type:text/plain" localhost:8500/v1/kv/config/SWAGGER-AGGREGATOR/data --data-binary @- < ../config/SWAGGER-AGGREGATOR-default.yml

