## Bootstrap tests

The bootstrap tests require an http repository for OS installation images.
The repo is defined as a URL in the GLOBAL_CONFIG['repos']['mirror'] configuration field.
All OS installation images must be in subdirectories under that base URL.
Each individual OS repo is defined in the GLOBAL_CONFIG['repos']['os']['osname'] configuration fields. See the config file README for additional info.

The test framework configures the OS install repo via the RackHD 'proxy' feature, which is configured via the deploy scripts.
Eack individual OS repo is defined relative to the appliance control network IP address.

Examples:

    "os": {
      "esxi55": "http://172.31.128.1:8080/mirror/esxi/5.5/esxi",
      "esxi60": "http://172.31.128.1:8080/mirror/esxi/6.0/esxi6",
      "centos65": "http://172.31.128.1:8080/mirror/centos/6.5/os/x86_64",
      "centos70": "http://172.31.128.1:8080/mirror/centos/7/os/x86_64",
      "rhel70": "http://172.31.128.1:8080/mirror/rhel/7.0/os/x86_64"
    },
    }

The bootstrap test scripts will only test the OS types that are defined in the global config file. All others will be skipped.
