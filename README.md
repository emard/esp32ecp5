# ESP32 JTAG tap walker for ECP5

This is micropython running on ESP32 to allow
JTAG programming and flashing of Lattice ECP5 FPGA JTAG.
A simple way in about 700 lines of code.

# Quick Start

New ULX3S boards v3.1.x may have already installed micropython and esp32ecp5
with setup that helps setting WiFi password and board pinout.
Connect USB to US1 port. With terminal emulator open port
"/dev/ttyUSB0" (linux) or "COM1:" (windows) at standard speed 115200,8n1
Reboot ESP32, type this and follow interactive setup procedure:

    import ecp5setup

Reboot ESP32. If connected to internet,
esp32ecp5 can be installed or upgraded online with
[upip.install("esp32ecp5")](https://pypi.org/project/esp32ecp5):

    import upip
    upip.install("esp32ecp5")
    Installing to: /lib/
    Warning: micropython.org SSL certificate is not validated
    Installing esp32ecp5 1.0.6 from https://files.pythonhosted.org/packages/a1/a5/b3689848cabb12c785bb402093180b2a20e180e158692fc19c383b30fac8/esp32ecp5-1.0.6.tar.gz

It can be also upgraded from FTP or LFTP prompt:

    ftp> site import upip; upip.install(\"esp32ecp5\")
    lftp> site "import upip; upip.install(\"esp32ecp5\")"
    250-
    Installing to: /lib/
    Installing esp32ecp5 1.0.12 from https://files.pythonhosted.org/packages/46/d6/15b3f9f2312b4bc16f9c2d0c042ad4e4ae8aee969c50b352d816b090a8b0/esp32ecp5-1.0.12.tar.gz
    250 OK

# Install ESP32 micropython

Skip this step if you have ESP32 on some development board with USB-serial module.
If you have ESP32 on [ULX3S board](https://github.com/emard/ulx3s), you need to 
download [passthru bitstream for ULX3S](https://github.com/emard/ulx3s-bin/tree/master/fpga/passthru),
Choose appropriate for your board and ECP5 chip and upload passthru bitstream to flash

    fujprog -j flash passthru.bit

Download [micropython for ESP32](https://micropython.org/download#esp32)
"Stable" version.
For WROOM modules use non-SPIRAM versions like:
[esp32-idf3-20210202-v1.14.bin](https://micropython.org/resources/firmware/esp32-idf3-20210202-v1.14.bin).
Non-SPIRAM will work for WROVER modules too,
but to use extra RAM, WROVER modules need SPIRAM versions like:
[esp32spiram-idf3-20210202-v1.14.bin](https://micropython.org/resources/firmware/esp32spiram-idf3-20210202-v1.14.bin).
Versions v1.12 - v1.16 built with idf3 and idf4 should all work.
idf3 v1.14 build is recommended as the latest version 
which can mount and unmount SD card multiple times.
idf3 leaves slighty more free RAM than idf4 builds,
and ESP32-WROOM modules always need more RAM.

    wget https://micropython.org/resources/firmware/esp32-idf3-20210202-v1.14.bin

Upload micropython to ESP32

    esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
    esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-idf3-20210202-v1.14.bin

Power off and on ESP32

# ESP32 micropython prompt

Connect over USB-serial

    screen /dev/ttyUSB0 115200

Press few ENTERs, you should see prompt

    >>>
    >>>

Try some simple commands

    >>> 1+2
    3
    >>> print("hey")
    hey

# Connect ESP32 to WiFi

This is how to manually setup WiFi by creating auto-executable file
named "main.py" by copy-pasting text to ">>>" micropython command prompt
without any upload tools.
In following chapters is explained how to install upload tools
and setup simple roaming profile with multiple
APs and passwords.

Choose either setup as "client" or "access point":

Setup as client that logs on to a WiFi access point (home internet router),
replace "accesspoint" and "password" with proper logins for your WiFi router:

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

Setup as access point.
Some WiFi clients may have problem connecting to ESP32.

    f=open("main.py","w")
    f.write("import network\n")
    f.write("ap_if = network.WLAN(network.AP_IF)\n")
    f.write("ap_if.active(True)\n")
    f.write('ap_if.config(essid="accesspoint", password="password")\n')
    f.write("import uftpd\n")
    f.close()
    import webrepl_setup

It will prompt to ask few questions:
Enable "webrepl" by choosing "E".
Type and repeat any password you like, "webrepl" client will later ask for this password.
Finally agree to reboot ESP32. It will automatically create "boot.py" file:

    # This file is executed on every boot (including wake-boot from deepsleep)
    #import esp
    #esp.osdebug(None)
    import webrepl
    webrepl.start()

After reboot and successful WiFi connection,
it will print its IP address (192.168.4.1).

    I (1554) network: CONNECTED
    I (2824) event: sta ip: 192.168.4.1, mask: 255.255.255.0, gw: 192.168.4.2

You can always soft-reboot again to see IP
address if you press Ctrl-D on empty python prompt:

    >>> Ctrl-D

# Upload files from web browser

With web browser open [webrepl for web browser](http://micropython.org/webrepl),
enter IP address of ESP32, enter password. Python prompt ">>>" should appear.

From webrepl GUI minimal upload is "ecp5.py" and "jtagpin.py" to root "/" or
"/lib" directory at the ESP32.
Very useful are also "uftpd.py", "sdraw.py", "wifiman.py", "ecp5wp.py",
"ecp5setup.py".
Your passwords can be placed in "wifiman.conf" and uploaded to root "/" of
ESP32 or generated automatically with "import ecp5setup".
For details about FTP and roaming profiles read below.
Optionally upload some bitstream file like "blink.bit" or
"blink.bit.gz" (compressed with "gzip4k.py" tool) to
the root of ESP32.

If webrepl GUI disconnects immediatly, without asking the password, try to delete
web browser's history, cookies, passwords and similar data, close web browser and
try again.

# Upload files over USB from linux command line

Get Adafruit "ampy"

    pip3 install adafruit-ampy

It will be installed here:

    ~/.local/bin/ampy

Upload local file "main.py" to ESP32 like this:

    ampy -p /dev/ttyUSB0 put main.py

List files on ESP32:

    ampy -p /dev/ttyUSB0 ls
    /boot.py
    /main.py
    ...

# Upload files over WiFi from linux command line

Get [webrepl for commandline](https://github.com/Hermann-SW/webrepl),
and [KOST's webrepl shell automation](https://github.com/kost/webrepl-python)
install some python dependencies:

    apt-get install python-websocket

To install commandline REPL, just copy 5 files giving them
typeable names and make them executable:

    cp websocket_helper.py /usr/local/bin/websocket_helper.py
    cp webrepl_client.py /usr/local/bin/replsh
    cp webrepl_cli.py /usr/local/bin/replcp
    cp webrepl.py /usr/local/bin/webrepl.py
    cp scripts/webreplcmd /usr/local/bin/replcmd
    chmod +x /usr/local/bin/replsh /usr/local/bin/replcp /usr/local/bin/replcmd

Upload local files to remote ESP32 like this:

    replcp -p password ecp5.py 192.168.4.1:ecp5.py

or like this:

    replcmd --host=192.168.4.1 --password=1234 put ecp5.py ecp5.py

For prompt without being asked password:

    replsh -p password -r 192.168.4.1

For prompt with password asked:

    replsh 192.168.4.1

Soft-reboot ESP32 by entering uppercase "D" to empty
prompt and press "ENTER" (instead of Ctrl-D from web GUI)

    >>> D

List directory to see if the files are uploaded:

    import os
    os.listdir()
    ['boot.py', 'ecp5.py', 'main.py', 'blink.bit']

# WiFi manager for roaming

"wifiman.py" is a simple WiFi roaming manager which scans WiFi
access points at power-on and uses password from file "wifiman.conf":
(newline char after each line, no comments, no emtpy lines)

    accesspoint1:password1
    accesspoint2:password2

Then "main.py" should be only this

    import wifiman
    import uftpd
    from ntptime import settime
    try:
      settime()
    except:
      print("NTP not available")


# ECP5 programming from python command line

    import ecp5
    ecp5.prog("blink.bit") 
    99262 bytes uploaded in 142 ms (675 kB/s)

    ecp5.prog("filepath_or_url") uploads to FPGA SRAM.
    ecp5.flash("filepath_or_url", addr=0x000000) uploads to SPI CONFIG FLASH

upload to FLASH will start at byte address specified by "addr".
which should be 4K even - lower 12 bits must be 0x000

If file ends with "*.gz", it will be decompressed on-the-fly.

    linux$ ./gzip4k.py blink.bit blink.bit.gz
    >>> ecp5.prog("http://192.168.4.2/blink.bit.gz")
    >>> ecp5.flash("blink.bit.gz")

For bitstreams stored on the web server or SD card, 
".bit" files are recommended, with bitstream compression enabled
using --compress option from trellis tools.
For bitstreams stored on ESP32 internal FLASH,
both --compress and gzipped files ".bit.gz" are recommended for
FLASH space saving.

SD card usage (SPI at gpio 12-15):

    import os,machine
    os.mount(machine.SDCard(slot=3),"/sd")
    os.listdir("/sd")

"slot=3" must be specified to prevent using SD card MMC mode.
MMC mode is about 2x faster but currently it doesn't work together
with this ecp5.py programmer.

# FLASH protection

FLASH chip can set hardware write protection to a part of address space
and "ecp5wp.py" is ESP32 command line tool for protection and
unprotection. Supported FLASH chips are ISSI IS25LP128 and Winbond
W25Q128.

    import ecp5wp

Tool will autodetect FLASH chip, report current protection status
and suggest commands to protect or unprotect first 2MB usually used
to hold bootloader bitstream.

Be careful with setting OTP registers, it is possible to permanently
lock the chip.

# ECP5 programming from FTP

Here I have "uftpd.py" which came from original
[ESP32 FTP server](https://github.com/robert-hh/FTP-Server-for-ESP8266-ESP32-and-PYBD)
with my small modifications to support "ecp5.py" programmer.
Install FTP server by uploading "uftpd.py" file to the root of ESP32 filesystem:
and start it with:

    import uftpd
    FTP server started on 192.168.4.1:21

Get ftp client "ftp" or "lftp". I tried them both and they work,
other clients I haven't tried...

    apt-get install ftp lftp

Connect with ftp client to ESP32, type ENTER at (empty) password

    ftp 192.168.4.1
    Connected to 192.168.5.72.
    220 Hello, this is the ULX3S.
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
try to toggle "passive" FTP mode. If FTP client is behind the firewall
it may work with passive mode on, close/open connection or try another 
FTP client.

    ftp> passive
    Passive mode on.
    ftp> close
    ftp> open 192.168.4.1

Besides normal FTP commands like "ls", "cd", "mkdir", "rmdir", "put", "get", "del",
it also accepts "site" command to read file from ESP32 local filesystem
(FLASH or SD card) and program FPGA:

    ftp> site http://192.168.4.2/blink.bit
    ... will program remote file to FPGA using
    ... ecp5.prog("/http:/192.168.4.2/blink.bit")
    ftp> site filename.bit
    ... will program local file to FPGA using
    ... ecp5.prog("filename.bit")
    ftp> site /sd/blink.bit
    ... If the path starts with "/sd/" then SD card will be unmounted
    ... before starting bitstream
    ftp> site passthru()
    ... program file "passthru%08X.bit.gz" % idcode
    ... ecp5.passthru()

SD card with FAT filesystem can be mounted or unmounted to "/sd" directory:

    ftp> site mount()
    ftp> ls sd
    ftp> site umount()
    ftp> ls sd

"site" can exec() any micropython command.
Quotes ("") and backslash escaping may be required. Actual syntax may vary
between ftp clients.

    ftp> site import ecp5; ecp5.passthru()
    lftp> site "import ecp5; ecp5.passthru()"
    250-                                                                
    ecp5.prog("passthru41113043.bit.gz")
    Warning: SPI(-1, ...) is deprecated, use SoftSPI(...) instead
    282624 bytes uploaded in 613 ms (461 kB/s)
    250 OK
    lftp> site ecp5.flash(\"passthru41113043.bit.gz\",0x200000)
    250-                                                                                  
    Warning: SPI(-1, ...) is deprecated, use SoftSPI(...) instead
    0x200000 4K wwwwwwwwwwwwwwww
    0x210000 4K wwwwwwwww
    102400 bytes uploaded in 5890 ms (17 kB/s)
    4K blocks: 25 total, 25 erased, 25 written.

Theoretically "site" should work well if there is enough RAM
but even on ESP32-WROVER with 2MB there is instability.
After few ecp5.prog() or ecp5.flash(), FTP traffic stops
and ESP32 freezes.

It is possible to directly put a binary file
(not gzipped) from "ftp>" prompt into FPGA, FLASH or
SD card (as raw image) using special destination file
name "fpga", "flash@" or "sd@".

    ftp> put blink.bit fpga
    ftp> put blink.bit flash@0
    ftp> put blink.bit flash@0x200000
    ftp> put freedos.img sd@0
    ftp> put freedos.img sd@0x200000
    ftp> put bios.img sd@-8192

NOTE: FLASH and SD card accept byte offset after "@" character.
Offset must be rounded to 4096 bytes for FLASH and to 512 bytes for SD.
Negative offset can be used for writing relative to the end of SD card.
Special destination file names "fpga", "flash@", "sd@" are
used for direct programming and they don't relate to actual
files on ESP32 filesystem.

if using "lftp", syntax is different, use option "-o" and prepend "/" like this:

    lftp 192.168.4.1:/> put blink.bit -o /fpga
    lftp 192.168.4.1:/> put blink.bit -o /flash@0

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

# Releasing

This is developer's procedure how to upload.
Developer should register at [Python Package Index](pypi.org),
increase version number in pypi/setup.py,
build package and upload, type pypi username/password when asked:

    cd pypi
    make clean
    make check
    make upload

# Onboard Editor

ESP32 can run small [VT100 terminal editor](https://github.com/robert-hh/Micropython-Editor)
Upload files "pye_mp.py" and "help.txt".

    from pye_mp import pye
    pye("help.txt")

connected with fujprog -t

    QUIT: ctrl-q
    SAVE: ctrl-s

connected with screen /dev/ttyUSB0 115200

    QUIT: ctrl-a q
    SAVE: ctrl-a s

# LOW RAM

Instead of ESP32-WROOM, use ESP32-WROVER :)

ecp5, ftp, gzip decompression, buffers and other things in use
allocate RAM. Sometimes there won't be enough
free RAM for everything on ESP32-WROOM.
Best is to obtain ESP32-WROVER which has 2MB additional PSRAM.
ESP32-WROOM workaround is to avoid using gzip'd files or
don't import uftpd.

# JTAG info

[JTAG STATE GRAPH](https://www.xjtag.com/about-jtag/jtag-a-technical-overview/tap_state_machine1)

# TODO

    [x] on-the-fly gzip decompression
    [x] read flash content
    [x] from read, decide if block has to be erased
    [x] fix HTTP GET for binary file
    [x] write disk image to SD card
    [x] reuse currently separated code for file/web bit/bit.gz
    [x] integrate with ftp server like https://github.com/robert-hh/FTP-Server-for-ESP8266-ESP32-and-PYBD
    [ ] integrate with webrepl and file browser like https://github.com/hyperglitch/webrepl
    [x] ecp5.prog() should return True if OK, False if FAIL
    [x] optimize send_bit, n-1 bits in loop and last bit outside of loop
    [x] while read flash until same content as file, with retry
    [x] more progress for flashing
    [x] ftp put fpga/flash reports Done/Fail
    [x] mount/umount SD card from ftp prompt (just cd to /sd)?
    [x] specify flash address ftp> put file.bit flash@0x200000
    [x] site mount, exit, site umount Fail
    [ ] "site" command should execute some python script
    [ ] upip installation https://packaging.python.org/tutorials/packaging-projects/
        https://docs.micropython.org/en/latest/reference/packages.html


