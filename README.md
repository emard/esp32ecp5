# ESP32 JTAG tap walker for ECP5

This is micropython running on ESP32 to allow
JTAG programming and flashing of Lattice ECP5 FPGA JTAG.
A simple way in about 600 lines of code.

# Usage

Skip this step if you have ESP32 on some development board with USB-serial module.
If you have ESP32 on [ULX3S board](https://github.com/emard/ulx3s), you need to 
download [passthru bitstream for ULX3S](https://github.com/emard/ulx3s-bin/tree/master/fpga/passthru),
Choose appropriate for your board and ECP5 chip and upload passthru bitstream to flash

    ujprog -j flash passthru.bit

Download [micropython for ESP32](https://micropython.org/download#esp32)
I do not use "stable" version like "esp32-idf3-20190529-v1.11.bin".
I use idf3 daily fresh version like in this example, but I can't link
as filename parts "20191103" and "549-gf2ecfe8b8" change every day. 

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
or as client that logs on to your WiFi router

    help()
    ... follow instructions for wifi
    ... for convenience put autostart commands in "main.py"

example autostart file "main.py" which logs on to WiFi access point:

    import network
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.connect("accesspoint", "password")

example autostart file "main.py" which makes ESP32 to become WiFi access point:

    import network
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(True)
    ap_if.config(essid="accesspoint", password="password")

upload "ecp5.py", "main.py" and some bitstream file like "blink.bit" or
"blink.bit.gz" (compressed with gzip -9) to
the root of ESP32 python FLASH filesystem
using [micropython webrepl](http://micropython.org/webrepl).

List directory to see if the files are uploaded:

    import os
    os.listdir()
    ['boot.py', 'ecp5.py', 'main.py', 'blink.bit']

Yes there it is, let's try:

    import ecp5
    ecp5.program("blink.bit") 
    99262 bytes uploaded in 142 ms (675 kB/s)

    ecp5.program("filepath_or_url") uploads to FPGA SRAM.
    ecp5.flash("filepath_or_url", addr=0x000000) uploads to SPI CONFIG FLASH

upload to FLASH will start at byte address specified by "addr".
which should be 4K even - lower 12 bits must be 0x000

If file ends with "*.gz", it will be decompressed on-the-fly:

    linux$ gzip -9 blink.bit
    >>> ecp5.program("http://192.168.4.2/blink.bit.gz")
    >>> ecp5.flash("blink.bit.gz")

SD card usage (SPI at gpio 12-15):

    import os,machine
    os.mount(machine.SDCard(slot=3),"/sd")
    os.listdir("/sd")

"slot=3" must be specified to prevent using SD card MMC mode.
MMC mode is about 2x faster but currently it doesn't work together
with this ecp5.py programmer.

I have patched [ESP32 FTP
server](https://github.com/emard/FTP-Server-for-ESP8266-ESP32-and-PYBD).
Install FTP server by uploading 3 files to the root of ESP32 filesystem:

    ftp.py
    ftp_thread.py
    uftpd.py

Start it with:

    import uftpd

Besides normal FTP commands like "cd", "mkdir", "ls", "put", "get", "del",
it also accepts "site" command:

    ftp> site filename.bit
    ... will run ecp5.program("filename.bit")

To automate upload from linux shell,
enable ftp auto-login in "~/.netrc":

    cat ~/.netrc
    default login anonymous password user@site

A simple shell command can upload bitstream
with FTP and program ECP5:

    cat /usr/local/bin/ftpecp5prog
    #!/bin/sh
    ftp 192.168.4.1 <<EOF
    cd /sd/ULX3S # if SD is mounted
    put ${1}
    site ${1}
    EOF

use it as:

    ftpecp5prog blink.bit

# JTAG info

[JTAG STATE GRAPH](https://www.xjtag.com/about-jtag/jtag-a-technical-overview/tap_state_machine1)

# TODO

    [x] on-the-fly gzip decompression
    [x] read flash content
    [x] from read, decide if block has to be erased
    [x] fix HTTP GET for binary file
    [ ] write disk image to SD card https://docs.micropython.org/en/latest/library/uos.html
    [ ] reuse currently separated code for file/web bit/bit.gz
    [x] integrate with ftp server like https://github.com/robert-hh/FTP-Server-for-ESP8266-ESP32-and-PYBD
    [ ] integrate with webrepl and file browser like https://github.com/hyperglitch/webrepl
    [ ] ecp5.program() should return True if OK, False if FAIL
