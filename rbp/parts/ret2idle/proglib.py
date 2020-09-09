# micropython ESP32
# PROG common functions

# AUTHOR=EMARD
# LICENSE=BSD

# choose one:
#import ecp5lib as fpga
import artix7lib as fpga
#import cyclone5lib as fpga

import jtag
from jtag import *

def prog_stream(filedata, blocksize=4096):
  fpga.prog_open()
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
  fpga.prog_stream_done()

def prog(filepath, close=True):
  filedata, gz = filedata_gz(filepath)
  if filedata:
    if gz:
      prog_stream(filedata,blocksize=4096)
    else:
      prog_stream(filedata,blocksize=16384)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      return fpga.prog_close() # start the bitstream
    return True
  return False
