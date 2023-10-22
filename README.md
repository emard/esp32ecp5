# ESP32 JTAG tap walker for ECP5

Micropython on ESP32 or ESP32-S2 for
programming and flashing Lattice ECP5 FPGA via JTAG.
A simple way in about 700 lines of code.

# Quick Start

New ULX3S boards v3.1.x may have already installed micropython and esp32ecp5
with setup that helps setting WiFi password and board pinout.
Connect USB to US1 port. With terminal emulator open port
"/dev/ttyUSB0" (linux) or "COM1:" (windows) at standard speed 115200,8n1
Reboot ESP32, type this and follow interactive setup procedure:

    import ecp5setup

Reboot ESP32. If connected to internet:

# micropython 1.14 (recommended):

esp32ecp5 can be installed or upgraded online with
[upip.install("esp32ecp5")](https://pypi.org/project/esp32ecp5):

    import upip
    upip.install("esp32ecp5")
    Installing to: /lib/
    Warning: micropython.org SSL certificate is not validated
    Installing esp32ecp5 1.0.6 from https://files.pythonhosted.org/packages/a1/a5/b3689848cabb12c785bb402093180b2a20e180e158692fc19c383b30fac8/esp32ecp5-1.0.6.tar.gz

It can be also upgraded from FTP or LFTP prompt:

    ftp> site "import upip; upip.install('esp32ecp5')"
    lftp> site "import upip; upip.install('esp32ecp5')"
    250-
    Installing to: /lib/
    Installing esp32ecp5 1.0.12 from https://files.pythonhosted.org/packages/46/d6/15b3f9f2312b4bc16f9c2d0c042ad4e4ae8aee969c50b352d816b090a8b0/esp32ecp5-1.0.12.tar.gz
    250 OK

# micropython >= 1.21:

esp32ecp5 can be installed or upgraded online with mip

    import mip
    mip.install("https://raw.githubusercontent.com/emard/esp32ecp5/master")
    Installing https://raw.githubusercontent.com/emard/esp32ecp5/master/package.json to /lib
    Copying: /lib/ecp5.py
    Copying: /lib/uftpd.py
    Copying: /lib/wifiman.py
    Copying: /lib/sdraw.py
    Copying: /lib/ecp5wp.py
    Copying: /lib/ecp5setup.py
    Installing zlib (latest) from https://micropython.org/pi/v2 to /lib
    Copying: /lib/zlib.mpy
    Done

It can be also upgraded from FTP or LFTP prompt:

    ftp> site "import mip; mip.install('https://raw.githubusercontent.com/emard/esp32ecp5/master')"
    lftp> site "import mip; mip.install('https://raw.githubusercontent.com/emard/esp32ecp5/master')"
    250-
    Installing https://raw.githubusercontent.com/emard/esp32ecp5/master/package.json to /lib
    Copying: /lib/ecp5.py
    Copying: /lib/uftpd.py
    Copying: /lib/wifiman.py
    Copying: /lib/sdraw.py
    Copying: /lib/ecp5wp.py
    Copying: /lib/ecp5setup.py
    Installing zlib (latest) from https://micropython.org/pi/v2 to /lib
    Exists: /lib/zlib.mpy
    Done
    250 OK

# ESP32 pinout

JTAG needs to switch between bitbanging and hardware SPI mode.
Bitbanging is required to walk thru JTAG TAP states.
SPI is required for fast upload of large bitstream.

There is undocumented behaviour of possible glitch when switching
between bitbanging and hardware SPI. Glitch appears at "clk" line and
maybe some other too. Although bitstream is usually tolerant about
garbage data before and after, but it is best to avoid it.
Experimentally is determined this pinout which doesn't make
glitch at switching modes:

    tms   = 5   # BLUE LED - 549ohm - 3.3V
    tck   = 18
    tcknc = 21  # 1,2,3,19,21 free pin for SPI workaround
    tdi   = 23
    tdo   = 34
    led   = 19

"tcknc" is not connected, but it is important to
temporary replace "tck" to avoid glitch when changing
modes between bitbanging and SPI.

Activity indicator can be hi-efficiency LED with near 3V
drop (blue) and 0.5-1k series resistor connected between
"tms" and 3.3V.

There can be also separate LED connected at "led".

# Install ESP32 micropython

Skip this step if you have ESP32 on some development board with USB-serial module.
If you have ESP32 on [ULX3S board](https://github.com/emard/ulx3s), you need to 
download [passthru bitstream for ULX3S](https://github.com/emard/ulx3s-bin/tree/master/fpga/passthru),
Choose appropriate for your board and ECP5 chip and upload passthru bitstream to flash

    fujprog -j flash passthru.bit

For ESP32 classic download [micropython for ESP32](https://micropython.org/download#esp32)
"Stable" version.
For WROOM modules use non-SPIRAM IDF3 versions like:
[ESP32_GENERIC-IDF3-20210202-v1.14.bin](https://micropython.org/resources/firmware/ESP32_GENERIC-IDF3-20210202-v1.14.bin).
or
[ESP32_GENERIC-20231005-v1.21.0.bin](https://micropython.org/resources/firmware/ESP32_GENERIC-20231005-v1.21.0.bin).
Non-SPIRAM will work for WROVER modules too,
but to use extra RAM, WROVER modules need SPIRAM versions like:
[ESP32_GENERIC-SPIRAM-20210202-v1.14.bin](https://micropython.org/resources/firmware/ESP32_GENERIC-SPIRAM-20210202-v1.14.bin).
or
[ESP32_GENERIC-SPIRAM-20231005-v1.21.0.bin](https://micropython.org/resources/firmware/ESP32_GENERIC-SPIRAM-20231005-v1.21.0.bin)
v1.14 build is slightly old but widely tested, it
can mount and unmount SD card multiple times while
v1.15-v1.19 crash at next mount/umount.
v1.21 is new and full of fresh features,
most things work like on 1.14 but flashing of
FPGA SPI chip currently doesn't work.

    import gc
    print(gc.mem_free())

    wget https://micropython.org/resources/firmware/ESP32_GENERIC-IDF3-20210202-v1.14.bin

Upload micropython to ESP32

    esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
    esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-idf3-20210202-v1.14.bin

Power off and on ESP32

Micropython v1.12 can be used with small modifications:

    from machine import SPI, SoftSPI, Pin, freq
    # don't import SoftSPI, it doesn't exist on v1.12
    from machine import SPI, Pin, freq
    
    swspi=SoftSPI(baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(jtagpin.tck), mosi=Pin(jtagpin.tdi), miso=Pin(jtagpin.tdo))
    # SPI(-1, ...) is SoftSPI at v1.12
    swspi=SPI(-1, baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(jtagpin.tck), mosi=Pin(jtagpin.tdi), miso=Pin(jtagpin.tdo))

# ESP32-S2 pinout

This pinout is not yet tested does it glitch at
changing modes. It is possible that there are
better combinations.

This pinout provides 40KB/s flashing speed. Different
pinout was tried and it provides only 20KB/s. It is not
yet known is there a pinout able to write flash faster
than 40KB/s.

ESP32-S2 can use any pin as input and/or output,
while at ESP32 classic, pins 32 and higer are input only.

Some micropython for ESP32-S2 binary builds prevent
use of some pins as input or output, not yet known why.
This is experimentally found pinout that is accepted
and works:

    tms   = 8   # BLUE LED - 549ohm - 3.3V
    tck   = 16
    tdi   = 15
    tdo   = 7
    tcknc = 12  # free pin for SPI workaround
    led   = 13

# Install ESP32-S2 micropython

ESP32-S2 modules with PSRAM and native USB support can be used.
ESP32-S2 modules without PSRAM don't have enough RAM for esp32ecp5.
Download [micropython for ESP32-S2](https://www.wemos.cc/en/latest/tutorials/s2/get_started_with_micropython_s2.html).
This firware doesn't currently support SD card.
It should be recompiled and configured to support SD
and open 2nd USB-serial port which will be transparently routed
to hardware TX/RX pins for communication with various FPGA projects
that need serial port.

Use this pinout:

    GND  GND
    3V3  3.3V
    EN   10k 3.3V
    IO0  BTN GND
    IO18 10k 3.3V (pullup for floating RXD)
    IO19 D-
    IO20 D+
    # JTAG pinout
    IO15 TDI
    IO16 TCK
    IO7  TDO
    IO8  TMS - BLUE LED - 549ohm - 3.3V

Enter USB download mode by connecting GPIO0 to GND and plugging USB.
Upload micropython firmware:

    esptool.py --port /dev/ttyACM0 --baud 1000000 erase_flash
    esptool.py --port /dev/ttyACM0 --baud 1000000 write_flash -z 0x1000 s2_mini_micropython_v1.16-200-g1b87e1793.bin

Unplug USB, disconnect GPIO0 from GND and re-plug USB.
Serial port "/dev/ttyACM0" will appear, providing micropython prompt:

    screen /dev/ttyACM0

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

Get micropython's "mpremote"

    pipx install mpremote

Get prompt:

    mpremote connect /dev/ttyUSB0
    >>>

List files:

    mpremote connect /dev/ttyUSB0 ls
    ls :
         137 boot.py
         114 jtagpin.py

Upload local files to ESP32 like this:

    mpremote connect /dev/ttyUSB0 mkdir lib
    mpremote connect /dev/ttyUSB0 cp ecp5.py uftpd.py sdraw.py ecp5wp.py ecp5setup.py wifiman.py :/lib/

Get Adafruit "ampy"

    pipx install adafruit-ampy

It will be installed here:

    ~/.local/bin/ampy

Upload local files to ESP32 like this (script "upload.sh"):

    ampy -p /dev/ttyUSB0 mkdir /lib
    ampy -p /dev/ttyUSB0 put ecp5.py /lib/ecp5.py
    ampy -p /dev/ttyUSB0 put uftpd.py /lib/uftpd.py
    ampy -p /dev/ttyUSB0 put sdraw.py /lib/sdraw.py
    ampy -p /dev/ttyUSB0 put ecp5wp.py /lib/ecp5wp.py
    ampy -p /dev/ttyUSB0 put ecp5setup.py /lib/ecp5setup.py
    ampy -p /dev/ttyUSB0 put wifiman.py /lib/wifiman.py
    ampy -p /dev/ttyUSB0 put wifiman.conf /wifiman.conf
    ampy -p /dev/ttyUSB0 put jtagpin.py /jtagpin.py
    ampy -p /dev/ttyUSB0 put sdpin.py /sdpin.py
    ampy -p /dev/ttyUSB0 put main.py /main.py

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

FPGA ECP5 should be loaded with bitstream that allows
FLASH access from JTAG
(SYSCONFIG MASTER_SPI_PORT=ENABLE in .lpf, without
using USRMCLK module in user design)
and drives WPn=1 and HOLDn=1 to prevent crosstalk.

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
If command needs quotes, use double quotes outside and single quotes inside:

    lftp> site "print('abc')"

Actual syntax may vary between ftp clients.

    ftp> site import ecp5; ecp5.passthru()
    lftp> site "import ecp5; ecp5.passthru()"
    250-                                                                
    ecp5.prog("passthru41113043.bit.gz")
    282624 bytes uploaded in 613 ms (461 kB/s)
    250 OK
    lftp> site "ecp5.flash('passthru41113043.bit.gz',0x200000)"
    250-                                                                                  
    0x200000 4K wwwwwwwwwwwwwwww
    0x210000 4K wwwwwwwww
    102400 bytes uploaded in 5890 ms (17 kB/s)
    4K blocks: 25 total, 25 erased, 25 written.

Theoretically "site" should work well if there is enough RAM.
During upload of bitstream FPGA lines may have unpredictable
state. If a glitch occurs at ESP32 "EN" and other
pins, ESP32 may reset or freeze (stop responding)
until next power off/on cycle.

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

if using "lftp", syntax is different, use option "-o" like this:

    lftp 192.168.4.1:/> put blink.bit -o fpga
    lftp 192.168.4.1:/> put blink.bit -o flash@0

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


