# ESP32 JTAG tap walker for ECP5

ESP32 micropython demo for accessing ECP5 JTAG tap, a simple way.
Currently it can only read ECP5 IDCODE:

# Usage

Setup webrepl

    import webrepl_setup

reboot ESP32 and login to your wifi router

    help()
    ... follow instructions for wifi

upload tapwalk.py to root of ESP32 python FLASH filesystem
using webrepl.

List directory to check is it uploaded:

    import os
    os.listdir()
    ['boot.py', 'tapwalk.py', 'blink.bit']

Run the demo code:

    import tapwalk
    t=tapwalk.tapwalk()
    t.idcode()
    43101141

This does't work yet

    t.program("blink.bit")

# JTAG info

[JTAG STATE GRAPH](https://www.xjtag.com/about-jtag/jtag-a-technical-overview/tap_state_machine1)