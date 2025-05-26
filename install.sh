#!/bin/sh

PORT=/dev/ttyACM0
MPREMOTE=~/.local/bin/mpremote

$MPREMOTE connect $PORT mkdir :/lib
$MPREMOTE connect $PORT cp ecp5.py :/lib/ecp5.py
$MPREMOTE connect $PORT cp uftpd.py :/lib/uftpd.py
$MPREMOTE connect $PORT cp sdraw.py :/lib/sdraw.py
$MPREMOTE connect $PORT cp ecp5wp.py :/lib/ecp5wp.py
$MPREMOTE connect $PORT cp ecp5setup.py :/lib/ecp5setup.py
$MPREMOTE connect $PORT cp dfu.py :/lib/dfu.py
$MPREMOTE connect $PORT cp ptp.py :/lib/ptp.py
$MPREMOTE connect $PORT cp wifiman.py :/lib/wifiman.py
$MPREMOTE connect $PORT cp wifiman.conf :/wifiman.conf
$MPREMOTE connect $PORT cp jtagpin.py :/jtagpin.py
$MPREMOTE connect $PORT cp sdpin.py :/sdpin.py
$MPREMOTE connect $PORT cp main.py :/main.py
