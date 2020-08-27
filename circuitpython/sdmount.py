# download latest 6.x mpy bundle
# https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/
# cp -r adafruit_sdcard.py adafruit_bus_device /media/user/1234-5678/
import adafruit_sdcard
import busio
import digitalio
import board
import storage
# pinout http://elm-chan.org/docs/mmc/mmc_e.html
#   SD   SPI  (looking at contacts)
#  ------------
# | D1
# | D0   MISO
# | GND
# | CLK  CLK
# | VCC
# | GND
# | CMD  MOSI
# | D3   CSn
#  \ D2
#   -----------
gpio_csn  = board.IO34 # SD_D3
gpio_mosi = board.IO35 # SD_CMD
gpio_sck  = board.IO36 # SD_CLK
gpio_miso = board.IO37 # SD_D0
# Connect to the card and mount the filesystem.
spi = busio.SPI(gpio_sck, gpio_mosi, gpio_miso)
cs = digitalio.DigitalInOut(gpio_csn)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

import os
os.listdir("/sd")
