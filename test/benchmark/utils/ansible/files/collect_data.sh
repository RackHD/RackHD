#!/bin/bash

log_path="/tmp/benchmark_log"
interval=1
atop_procid=`ps aux | grep atop | sed "/grep\|netatop/d" | awk '{print $2}' | sort -r -n`
db_disk_procid=`ps aux | grep db_disk.sh | sed "/grep/d" | awk '{print $2}' | sort -r -n`

function terminate_process()
{
    # Kill existing atop process from the same user if any
    if [ "$1" ]; then
        for i in $1
        do
            kill -15 $i
            echo "kill process $i"
        done
    fi
}

function start_atop_collection()
{
    terminate_process $atop_procid

    # Get process PID
    ps aux | grep -E "(mongod|beam.smp|on-|dhcpd)" | sed '/grep/d' | awk -F ' ' '{print $2, $11, $12, $13}' > ${log_path}/pid.log

    # Get resource summary first
    atop 1 1 -oa | grep "elapsed\|Kbps" | grep -v "NET" > ${log_path}/summary.log

    # Monitor runtime data
    nohup sh -c "atop $interval -oa | grep "Kbps" | grep -v "NET"  > ${log_path}/cpu_mem_net_disk.log" 2>/dev/null &
}

function stop_atop_collection()
{
    terminate_process $atop_procid

    # Get resource summary at last
    atop 1 1 -oa | grep "elapsed\|Kbps" | grep -v "NET" >> ${log_path}/summary.log
}

function start_db_disk_collection()
{
    terminate_process $db_disk_procid
    nohup sh -c "./db_disk.sh -i $interval > ${log_path}/db_document.log" 2>/dev/null &
}

function stop_db_disk_collection()
{
    terminate_process $db_disk_procid
    ./db_disk.sh -s > ${log_path}/db_disk.log
}

function start_collection()
{
    start_atop_collection
    start_db_disk_collection
}

function stop_collection()
{
    stop_atop_collection
    stop_db_disk_collection
}

if [ $# -lt 1 ]; then
    echo "need an argument: -o [operation] -i [interval]"
    exit 0
fi

while getopts "i:o:" arg
do
    case $arg in
        i)
            interval=$OPTARG
            echo "set poller interval to: $interval"
            ;;
        o)
            case $OPTARG in
                start)
                    start_collection
                    ;;
                stop)
                    stop_collection
                    ;;
                ?)
                    echo "unknown parameter for -o"
                    exit 1
                    ;;
            esac
            ;;
        ?)
            echo "unknown argument"
            exit 1
            ;;
    esac
done
