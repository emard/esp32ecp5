# ESP32 JTAG tap walker for ECP5

This is micropython running on ESP32 to allow
JTAG programming and flashing of Lattice ECP5 FPGA JTAG.
A simple way in about 700 lines of code.

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

To automate further use, it is good to setup ESP32 to automatically
bring up networking and services after power up. This is done using
auto-executable file named "main.py".

Choose either: (copy-paste to usb-serial python prompt ">>>")

setup as client that logs on to WiFi access point (home internet router):

    f=open("main.py","w")
    f.write("import network\n")
    f.write("sta_if = network.WLAN(network.STA_IF)\n")
    f.write("sta_if.active(True)\n")
    f.write('sta_if.connect("accesspoint", "password")\n')
    f.write("import uftpd\n")
    f.close()
    import webrepl_setup

if client can't connect it will continuoulsy retry,
printing failure messages. Then it will be difficult to type
at usb-serial prompt. To stop it, type blindly or copy-paste:

    sta_if.disconnect()

or setup as access point:

    f=open("main.py","w")
    f.write("import network\n")
    f.write("ap_if = network.WLAN(network.AP_IF)\n")
    f.write("ap_if.active(True)\n")
    f.write('ap_if.config(essid="accesspoint", password="password")\n')
    f.write("import uftpd\n")
    import webrepl_setup

It will prompt to ask few questions:
Enable "webrepl" by choosing "E".
Type and repeat any password you like, "webrepl" service will later ask for this password.
Finally agree to reboot ESP32. After reboot and successful WiFi connection,
it will print its IP address. You can always soft-reboot again to see IP
address if you press Ctrl-D on empty python prompt:

    >>> Ctrl-D

with web browser open [micropython webrepl](http://micropython.org/webrepl),
enter IP address of ESP32 and upload "ecp5.py", (optionally also "uftpd.py"
if you want FTP server, read below) and some bitstream file like "blink.bit" or
"blink.bit.gz" (compressed with gzip -9) to
the root of ESP32 python FLASH filesystem

List directory to see if the files are uploaded:

    import os
    os.listdir()
    ['boot.py', 'ecp5.py', 'main.py', 'blink.bit']

Yes there it is, let's try:

    import ecp5
    ecp5.prog("blink.bit") 
    99262 bytes uploaded in 142 ms (675 kB/s)

    ecp5.prog("filepath_or_url") uploads to FPGA SRAM.
    ecp5.flash("filepath_or_url", addr=0x000000) uploads to SPI CONFIG FLASH

upload to FLASH will start at byte address specified by "addr".
which should be 4K even - lower 12 bits must be 0x000

If file ends with "*.gz", it will be decompressed on-the-fly.

    linux$ gzip -9 blink.bit
    >>> ecp5.prog("http://192.168.4.2/blink.bit.gz")
    >>> ecp5.flash("blink.bit.gz")

For bitstreams stored on the web server or SD card, 
".bin" files are recommended, with bitstream compression enabled
using --compress option from trellis tools.
For bitstreams stored on ESP32 internal FLASH,
".bin.gz" is recommended for FLASH space saving.

SD card usage (SPI at gpio 12-15):

    import os,machine
    os.mount(machine.SDCard(slot=3),"/sd")
    os.listdir("/sd")

"slot=3" must be specified to prevent using SD card MMC mode.
MMC mode is about 2x faster but currently it doesn't work together
with this ecp5.py programmer.

I have patched [ESP32 FTP
server](https://github.com/emard/FTP-Server-for-ESP8266-ESP32-and-PYBD).
Install FTP server by uploading "uftpd.py" file to the root of ESP32 filesystem:
and start it with:

    import uftpd
    FTP server started on 192.168.4.1:21

Get ftp client. I use only this, other may not work because
some things are hacky

    apt-get install ftp

Connect with ftp client to ESP32, type ENTER at (empty) password

    ftp 192.168.4.1
    Connected to 192.168.5.72.
    220 Hello, this is the ESP8266.
    230 Logged in.
    Remote system type is UNIX.
    Using binary mode to transfer files.
    ftp>

Try to list files, it should work like this:

    ftp> ls
    200 OK
    150 Directory listing:
    -rw-r--r-- 1 owner group        137 Jan  1 00:03 boot.py
    -rw-r--r-- 1 owner group        128 Jan  1 00:05 main.py
    -rw-r--r-- 1 owner group         14 Jan  1 00:05 webrepl_cfg.py
    -rw-r--r-- 1 owner group      19482 Jan  1 00:09 uftpd.py
    -rw-r--r-- 1 owner group      22777 Jan  1 00:10 ecp5.py
    -rw-r--r-- 1 owner group       5505 Jan  1 00:13 passthru21111043.bit.gz
    226 Done.

If you don't see listing similar to this, something is incompatible,
try to toggle "passive" FTP mode (for me it works for passive off and
doesn't work for passive on), close/open connection or try another 
FTP client.

    ftp> passive
    Passive mode off.
    ftp> close
    ftp> open 192.168.4.1

Besides normal FTP commands like "ls", "cd", "mkdir", "rmdir", "put", "get", "del",
it also accepts "site" command to program FPGA or upload to FLASH:

    ftp> site http://192.168.4.2/blink.bit
    ... will program remote file to FPGA using
    ... ecp5.prog("/http:/192.168.4.2/blink.bit")
    ftp> site filename.bit
    ... will program local file to FPGA using
    ... ecp5.prog("filename.bit")

It is possible to directly program a "*.bin" file
(not gzipped) from "ftp>" prompt directly to FPGA or FLASH
using special destination file name "fpga" or "flash":

    ftp> put blink.bit fpga
    ftp> put blink.bit flash

if using "lftp", syntax is different, use option "-o" like this:

    lftp 192.168.4.1:/> put blink.bit -o fpga
    lftp 192.168.4.1:/> put blink.bit -o flash

To automate upload from linux shell,
enable ftp auto-login in "~/.netrc":

    cat ~/.netrc
    default login anonymous password user@site

A simple shell command can upload bitstream
with FTP and program ECP5:

    cat /usr/local/bin/ftpecp5prog 
    #!/bin/sh
    ftp ${1} <<EOF
    put ${2} fpga
    EOF

use it as:

    ftpecp5prog 192.168.4.1 blink.bit

If FTP server is running and you try to program from "webrepl" and
it fails with a memory allocation error:

    ecp5.flash("blink.bit.gz")
    MemoryError: memory allocation failed, allocating 32768 bytes

Yes it happens to me all the time :). "esp32ecp5" constantly runs near out of memory.
Either disable FTP server by removing "import uftpd.py" from "main.py" file
and rebooting, or try workaround from ftp> commandline to issue any
"site" command just to let FTP server import ecp5 and then
memory situation will be better for ecp5.flash() from "webrepl"

    ... linux commandline
    ftp> site blink.bit.gz
    ... webrepl
    import ecp5
    ecp5.flash("blink.bit.gz")

# JTAG info

[JTAG STATE GRAPH](https://www.xjtag.com/about-jtag/jtag-a-technical-overview/tap_state_machine1)

# TODO

    [x] on-the-fly gzip decompression
    [x] read flash content
    [x] from read, decide if block has to be erased
    [x] fix HTTP GET for binary file
    [ ] write disk image to SD card https://docs.micropython.org/en/latest/library/uos.html
    [x] reuse currently separated code for file/web bit/bit.gz
    [x] integrate with ftp server like https://github.com/robert-hh/FTP-Server-for-ESP8266-ESP32-and-PYBD
    [ ] integrate with webrepl and file browser like https://github.com/hyperglitch/webrepl
    [x] ecp5.prog() should return True if OK, False if FAIL
    [x] optimize send_bit, n-1 bits in loop and last bit outside of loop
    [x] while read flash until same content as file, with retry
    [x] more progress for flashing
    [ ] put fpga/flash should report when bitstream fails to start
