# circuitpython ESP32S2
# ECP5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

# prog-only (no flash)
# memory saver that works with ESP32-S2 WROOM

from time import sleep,monotonic_ns
import board, busio, digitalio
from micropython import const
from struct import pack, unpack
from gc import collect

import jtag
from jtag import *

# call this before sending the bitstram
# FPGA will enter programming mode
# after this TAP will be in "shift DR" state
def prog_open():
  common_open()
  sir(b"\x46") # LSC_INIT_ADDRESS
  sdr_idle(b"\x01",2,10)
  sir(b"\x7A") # LSC_BITSTREAM_BURST
  # ---------- bitstream begin -----------
  send_tms(0) # -> capture DR
  #self.send_tms(0) # -> shift DR NOTE will be send during TCK glitch
  bitbang_jtag_off() # NOTE TCK glitch
  spi_jtag_on()

def prog_stream_done():
  # switch from hardware SPI to bitbanging done after prog_stream()
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
  #self.send_tms(0) # -> idle, disabled here as runtest_idle does the same
  runtest_idle(100, 10)
  # ---------- bitstream end -----------
  sir_idle(b"\xC0",2,1) # read usercode
  usercode = bytearray(4)
  sdr_response(usercode)
  check_response(unpack("<I",usercode)[0],expected=0,message="FAIL usercode")
  sir_idle(b"\x26",2,200) # ISC DISABLE
  sir_idle(b"\xFF",2,1) # BYPASS
  sir(b"\x3C") # LSC_READ_STATUS
  status = bytearray(4)
  sdr_response(status)
  status = unpack("<I",status)[0]
  check_response(status,mask=0x2100,expected=0x100,message="FAIL status")
  done = True
  if (status & 0x2100) != 0x100:
    done = False
  reset_tap()
  #self.led.value=0
  bitbang_jtag_input()
  bitbang_jtag_off()
  bitbang_tms_off()
  return done

def prog_stream(filedata, blocksize=16384):
  prog_open()
  bytes_uploaded = 0
  stopwatch_start()
  block = bytearray(blocksize)
  while True:
    if filedata.readinto(block):
      jtag.hwspi.write(block)
      bytes_uploaded += len(block)
    else:
      break
  stopwatch_stop(bytes_uploaded)
  prog_stream_done()

def prog(filepath, close=True):
  filedata, gz = filedata_gz(filepath)
  if filedata:
    if gz:
      prog_stream(filedata,blocksize=4096)
    else:
      prog_stream(filedata,blocksize=4096)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      return prog_close() # start the bitstream
    return True
  return False
