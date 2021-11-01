# MicroPython ESP32 JTAG programmer for FPGA

A MicroPython library that makes ESP32 a full featured JTAG programmer with FTP server.
Intended use is ULX3S board with ECP5 FPGA. Minimalistic code works on some hardware.
Not universal tool for special cases.

## Installation

Installation can be done using upip or by manually uploading it to the device.

## Easy Installation

Just install it using upip - standard micropython packaging.
```
import upip
upip.install('esp32ecp5')
```

## Manual Installation

Copy to your device (root or /lib folder), using ampy or webrepl.

```
ampy -p /dev/ttyUSB0 put ecp5.py
ampy -p /dev/ttyUSB0 put uftpd.py
ampy -p /dev/ttyUSB0 put sdraw.py
ampy -p /dev/ttyUSB0 put wifiman.py
```

# Usage

```python
import ecp5
ecp5.prog("blink.bit")
ecp5.flash("blink.bit")
```

# Development

Building for distribution:
```
python setup.py sdist
```

Distribution of release:
```
python setup.py sdist
pip install twine
twine check dist/*
twine upload dist/*
```

## Links

* [micropython.org](http://micropython.org)
* [Adafruit Ampy](https://learn.adafruit.com/micropython-basics-load-files-and-run-code/install-ampy)
* [ESP32 ECP5 JTAG by Emard](https://github.com/emard/esp32ecp5)

# License

Licensed under the [MIT License](http://opensource.org/licenses/MIT).
