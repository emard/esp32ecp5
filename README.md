# ESP32 JTAG tap walker for ECP5

ESP32 micropython demo for accessing ECP5 JTAG tap, a simple way.

# Usage

Download [passthru
bitstream](https://github.com/emard/ulx3s-bin/tree/master/fpga/passthru),
Choose appropriate for your board and upload passthru bitstream to flash

    ujprog -j flash passthru.bit

Download [micropython for ESP32](https://micropython.org/download#esp32)

    wget https://micropython.org/resources/firmware/esp32-idf3-20191103-v1.11-549-gf2ecfe8b8.bin

Upload micropython to ESP32

    esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
    esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-idf3-20191103-v1.11-549-gf2ecfe8b8.bin

Power off and on ESP32

Connect over USB-serial

    screen /dev/ttyUSB0 115200

Setup webrepl

    import webrepl_setup

Let it reboot ESP32 and setup ESP32 as access point
or as client that logs in to your wifi router

    help()
    ... follow instructions for wifi
    ... for convenience put autostart commands in "main.py"

example autostart file "main.py"

    import network
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect("accesspoint", "password")

upload "tapwalk.py", "main.py" and some bitstream file "blink.bit" to
the root of ESP32 python FLASH filesystem
using [micropython webrepl](http://micropython.org/webrepl).

List directory to see if the files are uploaded:

    import os
    os.listdir()
    ['boot.py', 'tapwalk.py', 'main.py', 'blink.bit']

Yes there it is, run the demo code:

    import tapwalk
    tap=tapwalk.tapwalk()
    tap.program("blink.bit")

SD card usage:

    import os,machine
    os.mount(machine.SDCard(slot=3),"/sd")
    os.listdir("/sd")

# JTAG info

[JTAG STATE GRAPH](https://www.xjtag.com/about-jtag/jtag-a-technical-overview/tap_state_machine1)
