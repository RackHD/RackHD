#!/bin/bash

echo "Setup mongo cluster"

mongo {{mongo_addr}} --eval "JSON.stringify(db.adminCommand({'replSetInitiate' : {{mongo_list}}}))" 
