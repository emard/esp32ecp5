# micropython ESP32
# FLASH common functions

# AUTHOR=EMARD
# LICENSE=BSD

# choose one:
#import ecp5lib as spi
import artix7lib as spi
#import cyclone5lib as spi

import jtag
from jtag import *

from uctypes import addressof

# data is bytearray of to-be-read length
def flash_read(data, addr=0):
  spi.flash_open()
  spi.flash_read_block(data, addr)
  spi.flash_close()

# accelerated compare flash and file block
# return value
# 0-must nothing, 1-must erase, 2-must write, 3-must erase and write
@micropython.viper
def compare_flash_file_buf(flash_b, file_b, must:int) -> int:
  flash_block = ptr8(addressof(flash_b))
  file_block = ptr8(addressof(file_b))
  l = int(len(file_b))
  for i in range(l):
    if (flash_block[i] & file_block[i]) != file_block[i]:
      must = 1
  if must: # erase will reset all bytes to 0xFF
    for i in range(l):
      if file_block[i] != 0xFF:
        must = 3
  else: # no erase
    for i in range(l):
      if flash_block[i] != file_block[i]:
        must = 2
  return must

# clever = read-compare-erase-write
# prevents flash wear when overwriting the same data
# needs more buffers: 4K erase block is max that fits on ESP32
# returns status True-OK False-Fail
def flash_stream(filedata, addr=0):
  spi.flash_open()
  addr_mask = spi.flash_erase_size-1
  if addr & addr_mask:
    print("addr must be rounded to flash_erase_size = %d bytes (& 0x%06X)" % (spi.flash_erase_size, 0xFFFFFF & ~addr_mask))
    return False
  addr = addr & 0xFFFFFF & ~addr_mask # rounded to even 64K (erase block)
  bytes_uploaded = 0
  stopwatch_start()
  #if 1:
  #  print("erase whole FLASH (max 90s)")
  #  sdr(b"\x60") # SPI WRITE ENABLE
  #  flash_wait_status(105)
  #  sdr(b"\xE3") # BULK ERASE (whole chip) rb[0x60]=0x06 or rb[0xC7]=0xE3
  #  flash_wait_status(90000)
  count_total = 0
  count_erase = 0
  count_write = 0
  file_block = bytearray(spi.flash_erase_size)
  flash_block = bytearray(spi.flash_read_size)
  progress_char="."
  while filedata.readinto(file_block):
    #led.value((bytes_uploaded >> 12)&1)
    retry = 3
    while retry >= 0:
      must = 0
      flash_rd = 0
      while flash_rd<spi.flash_erase_size:
        spi.flash_read_block(flash_block,addr+bytes_uploaded+flash_rd)
        must = compare_flash_file_buf(flash_block,file_block[flash_rd:flash_rd+spi.flash_read_size],must)
        flash_rd+=spi.flash_read_size
      write_addr = addr+bytes_uploaded
      if must == 0:
        if (write_addr & 0xFFFF) == 0:
          print("\r0x%06X %dK %c" % (write_addr, spi.flash_erase_size>>10, progress_char),end="")
        else:
          print(progress_char,end="")
        progress_char="."
        count_total += 1
        bytes_uploaded += len(file_block)
        break
      retry -= 1
      if must & 1: # must_erase:
        spi.flash_erase_block(write_addr)
        count_erase += 1
        progress_char = "e"
      if must & 2: # must_write:
        block_addr = 0
        next_block_addr = 0
        while next_block_addr < len(file_block):
          next_block_addr = block_addr+spi.flash_write_size
          spi.flash_write_block(file_block[block_addr:next_block_addr], addr=write_addr)
          write_addr += spi.flash_write_size
          block_addr = next_block_addr
        count_write += 1
        progress_char = "w"
      #if not verify:
      #  count_total += 1
      #  bytes_uploaded += len(file_block)
      #  break
    if retry < 0:
      break
  print("\r",end="")
  stopwatch_stop(bytes_uploaded)
  print("%dK blocks: %d total, %d erased, %d written." % (spi.flash_erase_size>>10, count_total, count_erase, count_write))
  return retry >= 0 # True if successful

def flash(filepath, addr=0, close=True):
  filedata, gz = filedata_gz(filepath)
  if filedata:
    status=flash_stream(filedata,addr)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      spi.flash_close() # start the bitstream
    return status
  return False

def flashrd(addr=0, length=1):
  data = bytearray(length)
  flash_read(data, addr)
  return data
