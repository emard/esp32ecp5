# ESP32 JTAG tap walker for ECP5

ESP32 micropython demo for accessing ECP5 JTAG tap, a simple way
in about 300 lines of code.

# Usage

Skip this step if you have ESP32 on some development board with USB-serial module.
If you have ESP32 on [ULX3S board](https://github.com/emard/ulx3s), you need to 
download [passthru bitstream for ULX3S](https://github.com/emard/ulx3s-bin/tree/master/fpga/passthru),
Choose appropriate for your board and ECP5 chip and upload passthru bitstream to flash

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

Enable it and let it reboot ESP32.

setup ESP32 as access point
or as client that logs in to your wifi router

    help()
    ... follow instructions for wifi
    ... for convenience put autostart commands in "main.py"

example autostart file "main.py"

    import network
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect("accesspoint", "password")

upload "ecp5.py", "main.py" and some bitstream file "blink.bit" to
the root of ESP32 python FLASH filesystem
using [micropython webrepl](http://micropython.org/webrepl).

List directory to see if the files are uploaded:

    import os
    os.listdir()
    ['boot.py', 'ecp5.py', 'main.py', 'blink.bit']

Yes there it is, let's try:


    import ecp5
    tap=ecp5.ecp5()
    tap.program("blink1.bit")
    99262 bytes uploaded in 0.069 s (1.405 MB/s)
    tap.program("http://192.168.4.2/blink2.bit")
    173895 bytes uploaded in 0.171 s (0.993 MB/s)

    tap.program("filepath_or_url") uploads to FPGA SRAM.
    tap.flash("filepath_or_url", addr=0x000000) uploads to SPI CONFIG FLASH 

upload to FLASH will start ad address specified by "addr".
which sould be 64K even - lower 16 bits must be 0x0000

SD card usage (SPI at gpio 12-15):

    import os,machine
    os.mount(machine.SDCard(slot=3),"/sd")
    os.listdir("/sd")

# JTAG info

[JTAG STATE GRAPH](https://www.xjtag.com/about-jtag/jtag-a-technical-overview/tap_state_machine1)

# TODO

    [ ] on-the-fly zlib decompression
 