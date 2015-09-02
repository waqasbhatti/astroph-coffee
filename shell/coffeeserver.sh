#!/bin/bash

# This file starts/stops/checks the astroph-coffee server

if [ $# -lt 1 ]
then
    echo "Usage: $0 start </path/to/astroph-coffee> [debugflag] [server port]"
    echo "       $0 stop"
    echo "       $0 status"
    exit 2
fi

ACTION=$1


if [ $ACTION == "start" ]
then

    if [ $# -lt 2 ]
    then
        echo "Usage: $0 start </path/to/astroph-coffee> [debugflag] [server port]"
        exit 2
    fi

    BASEPATH=$2

    if [ $# -ge 3 ]
    then
        DEBUGFLAG=$3
    else
        DEBUGFLAG=0
    fi

    if [ $# -ge 4 ]
    then
        SERVERPORT=$4
    else
        SERVERPORT=5005
    fi

    echo "astroph-coffee server directory: $BASEPATH"
    echo "astroph-coffee server port: $SERVERPORT"
    echo "astroph-coffee debug flag: $DEBUGFLAG"

    cd $BASEPATH/run
    source $BASEPATH/run/bin/activate

    # start the server
    nohup python $BASEPATH/run/coffeeserver.py --log_file_prefix=$BASEPATH/run/logs/coffeeserver.log --debugmode=$DEBUGFLAG --port=$SERVERPORT > $BASEPATH/run/logs/coffeeserver.stdout 2>&1 &

    echo "astroph-coffee server started at:" `date`
    ps -e --forest -o pid,user,vsz,rss,start_time,stat,args | grep -e 'coffeeserver\.py' | | grep $SERVERPORT | grep -v grep | grep -v emacs | grep -v ^vi
    deactivate

elif [ $ACTION == "stop" ]
then

    ps aux | grep -e 'coffeeserver\.py' | grep $SERVERPORT | grep -v ^vi | grep -v ps | grep -v emacs | awk '{ print $2 }' | xargs kill > /dev/null 2>&1
    echo "astroph-coffee server stopped at:" `date`


elif [ $ACTION == "status" ]
then

    echo "Server status: "
    ps -e --forest -o pid,user,vsz,rss,start_time,stat,args | grep -e 'coffeeserver\.py' | | grep $SERVERPORT | grep -v grep | grep -v emacs | grep -v ^vi
    echo

else
    echo "Usage: $0 start </path/to/astroph-coffee> [debugflag] [server port]"
    echo "       $0 stop"
    echo "       $0 status"

fi
