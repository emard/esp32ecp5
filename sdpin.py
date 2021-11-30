# ESP32 SD-SPI-MMC fixed pins
#d0=const(2)   # SD_D0   miso
#d1=const(4)   # SD_D1
#d2=const(12)  # SD_D2
#d3=const(13)  # SD_D3   csn
#clk=const(14) # SD_CLK  sck
#cmd=const(15) # SD_CMD  mosi
hiz=bytearray([2,4,12,13,14,15]) # to release SD

# ESP32-S2 SD-SPI user-defined pins
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
# Works with listed SD card pins connected directly to ESP32-S2.
# SD card pins D1,D2 are not connected.
# Additional pull up resistors are not used.

#d0=const(13)  # SD_D0   miso
#d3=const(10)  # SD_D3   csn
#clk=const(12) # SD_CLK  sck
#cmd=const(11) # SD_CMD  mosi
#hiz=bytearray([d0,d3,clk,cmd]) # to release SD
