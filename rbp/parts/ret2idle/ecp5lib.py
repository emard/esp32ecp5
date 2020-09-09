# micropython ESP32
# ECP5 specific functions

# AUTHOR=EMARD
# LICENSE=BSD

from time import sleep_ms
from machine import Pin
from micropython import const
from struct import pack, unpack
from uctypes import addressof

import jtag
from jtag import *

flash_read_size = const(2048)
flash_write_size = const(256)
flash_erase_size = const(4096)
flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8, 262144:0xD8 } # erase commands from FLASH PDF
flash_erase_cmd = flash_erase_cmd[flash_erase_size]
read_status = bytearray([5])
status = bytearray(1)

def idcode():
  bitbang_jtag_on()
  #self.led.on()
  reset_tap()
  runtest_idle(1,0)
  sir(0xE0)
  id_bytes = bytearray(4)
  sdr_response(id_bytes)
  #led.off()
  bitbang_jtag_off()
  return unpack("<I", id_bytes)[0]

# common JTAG open for both program and flash
def common_open():
  jtag_open()
  #sir(b"\xE0") # read IDCODE
  #sdr(pack("<I",0), expected=pack("<I",0), message="IDCODE")
  sir(0x1C) # LSC_PRELOAD: program Bscan register
  sdr(bytearray([0xFF for i in range(64)]))
  sir(0xC6) # ISC ENABLE: Enable SRAM programming mode
  sdr_idle(b"\x00",2,10)
  sir_idle(0x3C,2,1) # LSC_READ_STATUS
  status = bytearray(4)
  sdr_response(status)
  check_response(unpack("<I",status)[0], mask=0x24040, expected=0, message="FAIL status")
  sir(0x0E) # ISC_ERASE: Erase the SRAM
  sdr_idle(b"\x01",2,10)
  sir_idle(0x3C,2,1) # LSC_READ_STATUS
  status = bytearray(4)
  sdr_response(status)
  check_response(unpack("<I",status)[0], mask=0xB000, expected=0, message="FAIL status")

# call this before sending the bitstram
# FPGA will enter programming mode
# after this TAP will be in "shift DR" state
def prog_open():
  common_open()
  sir(0x46) # LSC_INIT_ADDRESS
  sdr_idle(b"\x01",2,10)
  sir(0x7A) # LSC_BITSTREAM_BURST
  # ---------- bitstream begin -----------
  # manually walk the TAP
  # we will be sending one long DR command
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  # switch from bitbanging to SPI mode
  jtag.hwspi.init(sck=Pin(gpio_tck)) # 1 TCK-glitch? TDI=0
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
  #send_tms(0) # -> idle, disabled here as runtest_idle does the same
  runtest_idle(100,10)
  # ---------- bitstream end -----------
  sir_idle(0xC0,2,1) # read usercode
  usercode = bytearray(4)
  sdr_response(usercode)
  check_response(unpack("<I",usercode)[0],expected=0,message="FAIL usercode")
  sir_idle(0x26,2,200) # ISC DISABLE
  sir_idle(0xFF,2,1) # BYPASS
  sir(0x3C) # LSC_READ_STATUS
  status = bytearray(4)
  sdr_response(status)
  status = unpack("<I",status)[0]
  check_response(status,mask=0x2100,expected=0x100,message="FAIL status")
  done = True
  if (status & 0x2100) != 0x100:
    done = False
  reset_tap()
  #led.off()
  bitbang_jtag_off()
  return done

# call this before sending the flash image
# FPGA will enter flashing mode
# TAP should be in "select DR scan" state
@micropython.viper
def flash_open():
  common_open()
  reset_tap()
  runtest_idle(1,0)
  sir_idle(0xFF,32,0) # BYPASS
  sir(0x3A) # LSC_PROG_SPI
  sdr_idle(pack("<H",0x68FE),32,0)
  # ---------- flashing begin -----------
  # 0x60 and other SPI flash commands here are bitreverse() values
  # of flash commands found in SPI FLASH datasheet.
  # e.g. 0x1B here is actually 0xD8 in datasheet, 0x60 is is 0x06 etc.

@micropython.viper
def flash_wait_status(n:int):
  retry=n
  mask=1 # WIP bit (work-in-progress)
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  jtag.swspi.write(read_status) # READ STATUS REGISTER
  while retry > 0:
    jtag.swspi.readinto(status)
    if (int(status[0]) & mask) == 0:
      break
    sleep_ms(1)
    retry -= 1
  send_tms(1) # -> exit 1 DR # exit at byte incomplete
  #send_data_byte_reverse(0,1,8) # exit at byte complete
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan
  if retry <= 0:
    print("error %d flash status 0x%02X & 0x%02X != 0" % (n,status[0],mask))

def flash_erase_block(addr=0):
  sdr(b"\x60") # SPI WRITE ENABLE
  flash_wait_status(1001)
  # some chips won't clear WIP without this:
  #status = pack("<H",0x00A0) # READ STATUS REGISTER
  #sdr_response(status)
  #check_response(unpack("<H",status)[0],mask=0xC100,expected=0x4000)
  req = pack(">I", (flash_erase_cmd << 24) | (addr & 0xFFFFFF))
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  jtag.swspi.write(req[:-1])
  send_data_byte_reverse(req[-1],1,8) # last byte -> exit 1 DR
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan
  flash_wait_status(2002)

def flash_write_block(block, addr=0):
  sdr(b"\x60") # SPI WRITE ENABLE
  flash_wait_status(1003)
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  # bitreverse(0x40) = 0x02 -> 0x02000000
  jtag.swspi.write(pack(">I", 0x02000000 | (addr & 0xFFFFFF)))
  jtag.swspi.write(block[:-1]) # whole block except last byte
  send_data_byte_reverse(block[-1],1,8) # last byte -> exit 1 DR
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan
  flash_wait_status(1004)

# data is bytearray of to-be-read length
def flash_read_block(data, addr=0):
  # 0x0B is SPI flash fast read command
  sdr = pack(">I",0x03000000 | (addr & 0xFFFFFF))
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  jtag.swspi.write(sdr) # send SPI FLASH read command and address and dummy byte
  jtag.swspi.readinto(data) # retrieve whole block
  send_data_byte_reverse(0,1,8) # dummy read byte -> exit 1 DR
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan

# call this after uploading all of the flash blocks,
# this will exit FPGA flashing mode and start the bitstream
@micropython.viper
def flash_close():
  # switch from SPI to bitbanging
  # ---------- flashing end -----------
  sdr(b"\x20") # SPI WRITE DISABLE
  sir_idle(0xFF,100,1) # BYPASS
  sir_idle(0x26,2,200) # ISC DISABLE
  sir_idle(0xFF,2,1) # BYPASS
  sir(0x79) # LSC_REFRESH reload the bitstream from flash
  sdr_idle(b"\x00\x00\x00",2,100)
  spi_jtag_off()
  reset_tap()
  #led.off()
  bitbang_jtag_off()

def init():
  global irlen
  irlen=8

init()
