#! /bin/bash

interval=5

function get_summary()
{
    mongo pxe --eval "printjson(db.stats())" | sed '1,2d'
    du -sh /var/lib/mongodb/journal/
}

while getopts "i:s" arg
do
    case $arg in
        i)
            interval=$OPTARG
            ;;
        s)
            get_summary
            exit 0
            ;;
        ?)
            echo "unknown argument"
            exit 1
            ;;
    esac
done

while :
do
    mongo pxe --eval "printjson(db.stats())" | sed '1,2d'
    sleep $interval
done
