# micropython ESP32
# CYCLONE5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

# FIXME: prog fail doesn't report
# NOTE: replace FLASH code for artix7 with code for cyclone5

from time import sleep_ms
from machine import Pin
from micropython import const
from struct import pack, unpack
from uctypes import addressof

import jtag
from jtag import *
jtag.irlen=10
from proglib import *

flash_read_size = const(2048)
flash_write_size = const(256)
flash_erase_size = const(65536)
flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8, 262144:0xD8 } # erase commands from FLASH PDF
flash_erase_cmd = flash_erase_cmd[flash_erase_size]

magic=bytearray([0x59,0xA6,0x59,0xA6])
wrenable=magic+bytearray([0,8,6])
wrdisable=magic+bytearray([0,8,4])
read_status=magic+bytearray([0,16,5,0])
status=bytearray(2)
dummy4=bytearray(4)
none=bytearray(0)

def idcode():
  bitbang_jtag_on()
  #jtag.led.on()
  reset_tap()
  runtest_idle(1,0)
  sir(6)
  id_bytes = bytearray(4)
  sdr_response(id_bytes)
  #jtag.led.off()
  bitbang_jtag_off()
  return unpack("<I", id_bytes)[0]

# USER1 send a+b MSB first
# a can be 0-size
def user1_send(a,b):
  sir(2) # USER1
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  jtag.swspi.write(a)
  jtag.swspi.write(b[:-1])
  send_data_byte_reverse(b[-1],1,8) # last byte -> exit 1 DR
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan

# USER1 send a, recv b
# a can be 0-size
# after b, it reads one dummy bit
@micropython.viper
def user1_send_recv(a,b):
  sir(2) # USER1
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  jtag.swspi.write(a)
  jtag.swspi.readinto(b)
  send_tms(1) # -> exit 1 DR, dummy bit
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR

# common JTAG open for both program and flash
def common_open():
  spi_jtag_on()
  jtag.hwspi.init(sck=Pin(gpio_tcknc)) # avoid TCK-glitch
  bitbang_jtag_on()
  #jtag.led.on()
  reset_tap()
  runtest_idle(1,0)

# workaround to keep same sdr/sir
def workaround():
  send_tms(0) # -> capture DR
  send_tms(1) # -> exit 1 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan

# call this before sending the bitstram
# FPGA will enter programming mode
# after this TAP will be in "shift DR" state
def prog_open():
  common_open()
  sir(2)
  runtest_idle(8,2)
  workaround()
  # ---------- bitstream begin -----------
  # manually walk the TAP
  # we will be sending one long DR command
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR # NOTE sent with 1 TCK glitch
  # switch from bitbanging to SPI mode
  jtag.hwspi.init(sck=Pin(gpio_tck)) # 1 TCK-glitch TDI=0
  # we are lucky that format of the bitstream tolerates
  # any leading and trailing junk bits. If it weren't so,
  # HW SPI JTAG acceleration wouldn't work.
  # to upload the bitstream:
  # FAST SPI mode
  #hwspi.write(block)
  # SLOW bitbanging mode
  #for byte in block:
  #  send_data_byte_reverse(byte,0)

def prog_stream_done():
  # switch from hardware SPI to bitbanging done after prog_stream()
  jtag.hwspi.init(sck=Pin(gpio_tcknc)) # avoid TCK-glitch
  spi_jtag_off()

# call this after uploading all of the bitstream blocks,
# this will exit FPGA programming mode and start the bitstream
# returns status True-OK False-Fail
def prog_close():
  bitbang_jtag_on()
  send_tms(1) # -> exit 1 DR
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan
  runtest_idle(8,2)
  # ---------- bitstream end -----------
  sir(4)
  runtest_idle(165,0)
  workaround()
  errors=bytearray(108)
  sdr_response(errors)
  ok = (errors[20]&8)==8
  sir(3)
  runtest_idle(8,6)
  sir(0x3FF) # BYPASS
  runtest_idle(8,2)
  reset_tap()
  #jtag.led.off()
  bitbang_jtag_off()
  return ok

# call this before sending the flash image
# FPGA will enter flashing mode
# TAP should be in "select DR scan" state
@micropython.viper
def flash_open():
  file="jtagspi%08x.bit.gz" % idcode()
  prog_stream(open_file(file,True))
  if not prog_close():
    print("%s failed" % file)
  common_open()
  reset_tap()
  runtest_idle(1,0)
  # ---------- flashing begin -----------
  # 0x60 and other SPI flash commands here are bitreverse() values
  # of flash commands found in SPI FLASH datasheet.
  # e.g. 0x1B here is actually 0xD8 in datasheet, 0x60 is is 0x06 etc.

@micropython.viper
def flash_wait_status(n:int):
  retry=n
  while retry > 0:
    user1_send(none,read_status)
    user1_send_recv(none,status)
    if (int(status[1]) & 1) == 0:
      break
    sleep_ms(1)
    retry -= 1
  if retry <= 0:
    print("error %d flash status 0x%02X & 1 != 0" % (n,status[1]))

def flash_erase_block(addr=0):
  user1_send(none,wrenable)
  flash_wait_status(1001)
  req=magic+bytearray([0,32,flash_erase_cmd,addr>>16,addr>>8,addr]) # 6=SPI WRITE ENABLE
  user1_send(none,req)
  flash_wait_status(2002)

def flash_write_block(block, addr=0):
  user1_send(none,wrenable)
  flash_wait_status(114)
  # 6 = SPI WRITE ENABLE, 2 = WRITE BLOCK followed by 3-byte address and 256-byte data block
  bits=(4+len(block))*8
  req=magic+bytearray([bits>>8,bits,2,addr>>16,addr>>8,addr])
  user1_send(req,block)
  flash_wait_status(1004)

# data is bytearray of to-be-read length
# max 2048 bytes
def flash_read_block(data, addr=0):
  # first is the request 3=READ BLOCK, 3-byte address, 256-byte data
  bits=(len(data)+4)*8
  req=magic+bytearray([bits>>8,bits,3,addr>>16,addr>>8,addr])
  user1_send(req,data)
  # collects response from previous command
  user1_send_recv(dummy4,data)

# call this after uploading all of the flash blocks,
# this will exit FPGA flashing mode and start the bitstream
@micropython.viper
def flash_close():
  # switch from SPI to bitbanging
  # ---------- flashing end -----------
  user1_send(none,wrdisable)
  sir(0xD) # JSHUTDOWN
  sir(0xB) # JPROGRAM
  runtest_idle(2000,20)
  sir(0x3F) # BYPASS
  runtest_idle(2000,0)
  spi_jtag_off()
  reset_tap()
  #jtag.led.off()
  bitbang_jtag_off()
