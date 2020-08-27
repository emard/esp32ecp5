# Circuitpython port for ESP32-S2

ESP32-S2 is very interesting for its native USB support.
Currently S2 has circuitpyhton and no micropython.

Pinout:

    GND  GND
    3V3  3.3V
    EN   10k 3.3V
    IO0  BTN GND
    IO18 10k 3.3V (pullup for floating RXD)
    IO19 D-
    IO20 D+
    IO5  TMS - BLUE LED - 549ohm - 3.3V
    IO26 TCK
    IO33 TDI
    IO34 TDO

See also module internal schematics in
[ESP32-S2 WROVER datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s2-wrover_esp32-s2-wrover-i_datasheet_en.pdf)

To upload circuitpython hold BTN and plug in the board to PC USB.
Serial port "/dev/ttyACM0" should appear on linux, other OS should
get similar serial device with different name.
Using the latest esptool.py v3.0-dev upload the latest
circuitpython for
[Adafruit CircuitPython Saola-1 WROVER board](https://adafruit-circuit-python.s3.amazonaws.com/index.html?prefix=bin/espressif_saola_1_wrover/en_US/)

    wget -c https://adafruit-circuit-python.s3.amazonaws.com/bin/espressif_saola_1_wrover/en_US/adafruit-circuitpython-espressif_saola_1_wrover-en_US-20200825-5b1a1c7.bin
    python3 esptool.py --chip esp32s2 -p /dev/ttyACM0 --no-stub -b 460800 --before=default_reset --after=hard_reset write_flash --flash_mode qio --flash_freq 40m --flash_size 16MB 0x0000 $1

Power OFF/ON the board without pressing BTN.
S2 should now enumerate as USB-serial "/dev/ttyACM0" and 
USB-storage device "Espressif Saola 1 w/WROVER 1.0" what makes
it very practical, just copy "ecp5.py" and "blink.bit" to the
root of its filesystem and connect to its serial port:

    screen /dev/ttyACM0
    >>> from ecp5 import idcode,prog,flash,flash_read
    IDCODE: 0x21111043
    >>> prog("blink.bit")
    102400 bytes uploaded in 46 ms (2226 kB/s)
    True
    >>> flash("blink.bit")
    102400 bytes uploaded in 1924 ms (53 kB/s)
    4K blocks: 25 total, 0 erased, 0 written.
    True
    >>>

Circuitpython bugs: for the first time, prog("blink.bit")
may be syntax error, for the second time it will succeed:

    >>> from ecp5 import prog,flash
    IDCODE: 0x21111043
    >>> prog("blink.bit")
    Traceback (most recent call last):
    File "<stdin>", line 1
    SyntaxError: invalid syntax
    >>> prog("blink.bit")
    102400 bytes uploaded in 45 ms (2275 kB/s)
    True

To load "autostart.bit" bitstream at power ON, make "main.py":

    import ecp5
    ecp5.prog("autostart.bit")
    ecp5.idcode()

Last "ecp5.idcode()" is to release JTAG pins to high-Z mode
and allow external JTAG to program ECP5.

Uploading a new bitstream is easy - just overwrite new "autostart.bit" to
USB flash disk and power OFF/ON the board or restart circuitpython
by pressing Ctrl-D at empty prompt:

    >>> Ctrl-D

