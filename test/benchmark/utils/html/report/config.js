var configuration = 
{
    "CPU": {
        "CPU": {
            "Short Description": "CPU Utilization %",
            "Summary Description": "Max CPU Util",
            "unit": "%",
            "divide": 1,
            "Description": "The occupation percentage of this process " +
            "related to the available capacity for this resource on " +
            "system level.",
            "sum": false
        },
        "USRCPU": {
            "Short Description": "CPU Time Spent in User Mode",
            "Summary Description": "Total User CPU",
            "unit": "ms",
            "divide": 1000,
            "Description": "CPU time consumption of this process in user " +
            "mode, due to processing the own program text.",
            "sum": true
        },
        "SYSCPU": {
            "Short Description": "CPU Time Spent in Kernel Mode",
            "Summary Description": "Total Sys CPU",
            "unit": "ms",
            "divide": 1000,
            "Description": "CPU time consumption of this process in system " +
            "mode (kernel mode), " +
            "usually due to system call handling.",
            "sum": true
        }
    },
    "Memory": {
        "RSIZE": {
            "Short Description": "Resident Memory Size Used",
            "Summary Description": "Max Resident Size",
            "unit": "byte",
            "divide": 1000,
            "Description": "The total resident memory usage consumed by this " +
            "process (or user). Notice that the RSIZE of a process includes " +
            "all resident memory used by that process, even if certain " +
            "memory parts are shared with other processes (see also the " +
            "explanation of PSIZE). If a process has finished during the " +
            "last interval, no value is shown since resident memory " +
            "occupation is not part of the standard process accounting record.",
            "sum": true
        },
        "VSIZE": {
            "Short Description": "Virtual Memory Size Used",
            "Summary Description": "Max Virt Size",
            "unit": "byte",
            "divide": 1000,
            "Description": "The total virtual memory usage consumed by this " +
            "process (or user). If a process has finished during the last " +
            "interval, no value is shown since virtual memory occupation is " +
            "not part of the standard process accounting record.",
            "sum": true            
        }
    },
    "Disk": {
        "WRDSK": {
            "Short Description": "Bytes Written into Disk",
            "Summary Description": "Total Disk Wt",
            "unit": "byte",
            "divide": 1000,
            "Description": "The write data transfer issued physically on " +
            "disk (so writing to the disk cache is not accounted for). This " +
            "counter is maintained for the application process that writes " +
            "its data to the cache (assuming that this data is physically " +
            "transferred to disk later on). Notice that disk I/O needed for " +
            "swapping is not taken into account.",
            "sum": true
        },
        "RDDSK": {
            "Short Description": "Bytes Read from Disk",
            "Summary Description": "Total Disk Rd",
            "unit": "byte",
            "divide": 1000,
            "Description": "The read data transfer issued physically on disk " +
            "(so reading from the disk cache is not accounted for).",
            "sum": true
        }
    },
    "Network": {
        "RNET": {
            "Short Description": "Packages Received",
            "Summary Description": "Total Pkg Rcvd",
            "unit": "pkg",
            "divide": 1000,
            "Description": "The number of TCP and UDP packets received by " +
            "this process.",
            "sum": true
        },
        "SNET": {
            "Short Description": "Packages Sent",
            "Summary Description": "Total Pkg Sent",
            "unit": "pkg",
            "divide": 1000,
            "Description": "The number of TCP and UDP packets transmitted " +
            "by this process.",
            "sum": true
        },
        "RNETBW": {
            "Short Description": "Network Bandwidth for Receiving",
            "Summary Description": "Max BW Rcvd",
            "unit": "bps",
            "divide": 1000,
            "Description": "Total bandwidth for received TCP and UDP packets " +
            "consumed by this process  (bits-per-second). This value can be " +
            "compared with the value 'si' on interface level (used bandwidth " +
            "per interface).",
            "sum": false
        },
        "SNETBW": {
            "Short Description": "Network Bandwidth for Sending",
            "Summary Description": "Max BW Sent",
            "unit": "bps",
            "divide": 1000,
            "Description": "Total bandwidth for sent TCP and UDP packets " +
            "consumed by this process  (bits-per-second). This value can be " +
            "compared with the value 'so' on interface level (used bandwidth " +
            "per interface).",
            "sum": false
        }
    }    
};