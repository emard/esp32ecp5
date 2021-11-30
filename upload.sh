#!/bin/sh -e

PORT=/dev/ttyUSB0
AMPY=~/.local/bin/ampy

$AMPY -p $PORT mkdir /lib
$AMPY -p $PORT put ecp5.py /lib/ecp5.py
$AMPY -p $PORT put uftpd.py /lib/uftpd.py
$AMPY -p $PORT put sdraw.py /lib/sdraw.py
$AMPY -p $PORT put ecp5wp.py /lib/ecp5wp.py
$AMPY -p $PORT put ecp5setup.py /lib/ecp5setup.py
$AMPY -p $PORT put wifiman.conf /wifiman.conf
$AMPY -p $PORT put jtagpin.py /jtagpin.py
$AMPY -p $PORT put sdpin.py /sdpin.py
$AMPY -p $PORT put main.py /main.py
