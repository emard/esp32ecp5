# Circuitpython port for ESP32-S2

ESP32-S2 is very interesting for its native USB support.
Currently S2 has circuitpyhton and no micropython.

Pinout:

    GND  GND
    3V3  3.3V
    EN   10k 3.3V
    IO18 10k 3.3V
    IO19 D-
    IO20 D+
    IO5  TMS - BLUE LED - 549ohm - 3.3V
    IO26 TCK
    IO33 TDI
    IO34 TDO

S2 enumerates as USB-serial and USB-storage device what makes
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

To autostart bitstream "autostart.bit", make "main.py":

    import ecp5
    ecp5.prog("autostart.bit")
    ecp5.idcode()

Uploading a new bitstream is easy - just copy "autostart.bit" to
USB flash disk and power OFF/ON the board or restart circuitpython
by pressing Ctrl-D at empty prompt:

    >>> Ctrl-D

