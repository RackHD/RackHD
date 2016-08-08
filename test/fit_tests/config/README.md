## Test config files:

All test config files must reside in the config directory.
There are two required files: config/global_config.json and config/stack_config.json.

## Global config file:

The global config file specifies operating parameters and test environment.

    {
      "credentials": { # section for all usernames and passwords
        "hyper": [ # appliance hypervisor credentials, may be multiple, first is default
          {
            "username": "root",
            "password": "password"
          }
        ],
        "ora": [ # appliance admin credentials, may be multiple, first is default
          {
            "username": "onrack",
            "password": "onrack"
          }
        ],
        "bmc": [ # node or appliance bmc credentials, may be multiple, first is default
          {
            "username": "admin",
            "password": "admin"
          },
          {
            "username": "root",
            "password": "password"
          }
        ],
        "node": [ # node OS login credentials, may be multiple, first is default
          {
            "username": "root",
            "password": "password"
          },
          {
            "username": "onrack",
            "password": "onrack"
          }
        ],
        "switch": [ # switch login credentials, may be multiple, first is default
          {
            "username": "admin",
            "password": "password"
          }
        ],
        "pdu": [ # PDU login credentials, may be multiple, first is default
          {
            "username": "admn",
            "password": "admn"
          }
        ]
      },
    "snmp":{ # SNMP config data
        "community": "onrack"
    },
      "repos": { # list of all OS and package repositories
        "_comment": "This is the list of repositories for each category",
        "proxy": "http://proxy.lab.com:3128",
        "mirror": "http://mirrors.lab.com/mirrors",
        "os": { # all OS install repos
          "esxi55": "http://172.31.128.1:8080/mirror/esxi/5.5/esxi",
          "esxi60": "http://172.31.128.1:8080/mirror/esxi/6.0/esxi6",
          "centos65": "http://172.31.128.1:8080/mirror/centos/6.5/os/x86_64",
          "centos70": "http://172.31.128.1:8080/mirror/centos/7/os/x86_64",
          "rhel70": "http://172.31.128.1:8080/mirror/rhel/7.0/os/x86_64"
        },
        "install": { # RackHD and OnRack installation repos
          "template": "http://mirrors.lab.com/mirrors/ova/ubunutu16.ova", # OVA template
          "onrackova": "http://mirrors.lab.com/mirrors/ova/onrack.ova", # OnRack OVA install
          "onrack": "http://mirrors.lab.com/get/", # OnRack package install mirror
          "rackhd": "https://github.com/rackhd/" # RackHD Git repo
          },
        "skupack": [ # SKU pack repositories, may be multiple
          "https://github.com/RackHD/on-skupack"
          ],
      },
      "ports": { # default access ports
        "_comment": "These are the northbound rest API port assignments",
        "http": 8080,
        "https": 8443
      }
    }

## Stack config:

The stack config file specifies addresses and environment for the specific hardware under test.
A stack config file is required for running deployment scripts, but not test scripts if running on the appliance.
The stack config file is organized by stack label, which can be any alphanumeric key value.
The stack key is used to identify the hardware to be used with test scripts using the '-stack' argument.

Sample stack configuration file:

    {
    "stack1":{                           #alphanumeric stack label, can be any number of stacks defined
        "bmc": "stack1.bmc.lab",         #appliance bmc address (required)
        "control": "stack1.control.lab", #control switch admin address (optional)
        "data": "stack1.data.lab",       #data switch admin address (optional)
        "hyper": "stack1.esxi.lab",      #esxi hypervisor admin address (required only for esxi)
        "ora": "stack1.host.lab",        #appliance OVA admin address (required)
        "ovamac": "00:50:56:00:11:00",   #appliance OVA MAC address (required only for esxi)
        "pdu": "192.168.1.255",          #PDU admin address (optional)
        "type": "esxi"                   #deployment type: esxi, docker, linux (required)
    }


# Stack config override files:

Any stack config can be modified via a 'detail' file by loading it into the config dir.
A detail file can have any name but must have a .json extension.
The detail file will look like the sample above but may have additional elements.
Only the stack data in the specified keys will be overwritten.
The detail file must have all of the required fields because it will overwrite all initial values.
