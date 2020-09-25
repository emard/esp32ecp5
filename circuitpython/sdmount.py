# download latest 6.x mpy bundle
# https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/
# cp -r adafruit_sdcard.mpy adafruit_bus_device /media/user/CIRCUITPY/
import adafruit_sdcard
import busio
import digitalio
import board
import storage
#import ecp5p
#ecp5p.prog("sdbridge.bit")
# pinout http://elm-chan.org/docs/mmc/mmc_e.html
#   SD   SPI  (looking at contacts)
#  ____________
# |
# | D1
# | D0   MISO
# | GND  GND
# | CLK  CLK
# | VCC  3.3V
# | GND  GND
# | CMD  MOSI
# | D3   CSn
#  \ D2
#   \__________
# Works with only listed SD card pins connected directly to ESP32-S2.
# SD card pins D1,D2 are not connected.
# Additional pull up resistors are not used.
#
#gpio_csn  = board.IO34 # SD_D3
#gpio_mosi = board.IO35 # SD_CMD
#gpio_sck  = board.IO36 # SD_CLK
#gpio_miso = board.IO37 # SD_D0
# pinout for LILYGO TTGO T8 ESP32-S2 V1.1 ST77789 http://www.lilygo.cn/claprod_view.aspx?TypeId=21&Id=1322
# source https://github.com/Xinyuan-LilyGO/LilyGo-esp32s2-base/blob/master/main/app_main.c
gpio_csn  = board.IO10 # SD_D3
gpio_mosi = board.IO11 # SD_CMD
gpio_sck  = board.IO12 # SD_CLK
gpio_miso = board.IO13 # SD_D0
# Connect to the card and mount the filesystem.
csn = digitalio.DigitalInOut(gpio_csn)
csn.direction = digitalio.Direction.OUTPUT
csn.value = 1 # do not select SD before initialization
spi = busio.SPI(clock=gpio_sck, MOSI=gpio_mosi, MISO=gpio_miso)
sdcard = adafruit_sdcard.SDCard(spi, csn)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

import os
print(os.listdir("/sd"))
