# RBP onboard programmer

Use onboard FJC-ESP32-V0r2 module.

    JTAG  GPIO
     TMS   4
     TCK  16
     TDI  15
     TDO   2

# FFM external programmer

Connect ESP32-WROVER-E (on FROGO board) with female-female wires
to 10-pin header on FFM board.

Pinout:

    ESP32
    GPIO JTAG  ------
      18  TCK | 1  2 |
      34  TDO | 3  4 | 3.3V
       5  TMS   5  6 | 
              | 7  8 |
      23  TDI | 9 10 | GND
               ------

# ARTIX-7

artix7.prog() uses normal "bit" binary bitstreams.
To write bitstream to config FLASH, ESP32 can use bscan
bitstream (jtag-spi passthru) for xc3sprog
[bscan7.bit
source](https://github.com/f32c/f32c/tree/master/rtl/proj/xilinx/ffm-a7100/ffm_a7100_jtag_spi_bridge),
compressed with "gzip -9" and named with idcode for example:

    jtagspi%08x.bit.gz % idcode
    
    jtagspi13631093.bit.gz

# CYCLONE-5

cyclone5.prog() uses raw bitstream which should be extracted
from "svf" file using "cyclone5_svf2bit.py" tool which does
byte-reverse and bit-reverse in each byte:

    cyclone5_svf2bit.py bitstream.svf bitstream.bit
