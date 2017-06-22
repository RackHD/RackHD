#!/bin/bash
curl -X POST -H 'Content-Type: application/json' -d '{"name": "Graph.Dell.Wsman.ConfigServices", "options":{ "defaults": {"configServer": "http://localhost:46020"}}}' 'http://172.31.128.1:9090/api/2.0/workflows'
