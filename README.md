# ESP32 JTAG tap walker for ECP5

This is micropython running on ESP32 to allow
JTAG programming and flashing of Lattice ECP5 FPGA JTAG.
A simple way in about 500 lines of code.

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

upload "ecp5.py", "main.py" and some bitstream file "blink.bit.gz" to
the root of ESP32 python FLASH filesystem
using [micropython webrepl](http://micropython.org/webrepl).

List directory to see if the files are uploaded:

    import os
    os.listdir()
    ['boot.py', 'ecp5.py', 'main.py', 'blink.bit']

Yes there it is, let's try:

    import ecp5
    ecp5.program("blink.bit") 
    99262 bytes uploaded in 0.142 s (0.667 MB/s)
    ecp5.program("http://192.168.4.2/blink2.bit")
    173895 bytes uploaded in 0.171 s (0.993 MB/s)

    ecp5.program("filepath_or_url") uploads to FPGA SRAM.
    ecp5.flash("filepath_or_url", addr=0x000000) uploads to SPI CONFIG FLASH 

upload to FLASH will start at byte address specified by "addr".
which should be 64K even - lower 16 bits must be 0x0000

To save space on ESP32, bitstream can be compressed by gzip -9
and stored to ESP32 filesystem (gzipped on web not support yet).
If file ends with "*.gz", it will be decompressed on-the-fly:

    linux$ gzip -9 blink.bit
    >>> ecp5.program("blink.bit.gz")
    >>> ecp5.flash("blink.bit.gz")

SD card usage (SPI at gpio 12-15):

    import os,machine
    os.mount(machine.SDCard(slot=3),"/sd")
    os.listdir("/sd")

# JTAG info

[JTAG STATE GRAPH](https://www.xjtag.com/about-jtag/jtag-a-technical-overview/tap_state_machine1)

# TODO

    [x] on-the-fly gzip decompression
    [x] read flash content
    [ ] from read, decide if block has to be erased
    [ ] write disk image to SD card
