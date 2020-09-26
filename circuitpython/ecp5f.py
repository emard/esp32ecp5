# circuitpython ESP32S2
# ECP5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

from time import sleep,monotonic_ns
import board, busio, digitalio
from micropython import const
from struct import pack, unpack

import jtag
from jtag import *

flash_read_size = const(2048)
flash_write_size = const(256)
flash_erase_size = const(4096) # WROOM
flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8 } # erase commands from FLASH PDF
flash_erase_cmd = flash_erase_cmd[flash_erase_size]
flash_req = bytearray(4)
flash_reqmv = memoryview(flash_req)

# call this before sending the flash image
# FPGA will enter flashing mode
# TAP should be in "select DR scan" state
def flash_open():
  common_open()
  reset_tap()
  runtest_idle(1,0)
  sir_idle(b"\xFF",32,0) # BYPASS
  sir(b"\x3A") # LSC_PROG_SPI
  flash_req[0]=0xFE
  flash_req[1]=0x68
  sdr_idle(flash_reqmv[0:2],32,0)

def flash_wait_status():
  retry=50
  # read_status_register = pack("<H",0x00A0) # READ STATUS REGISTER
  while retry > 0:
    # always refresh status_register[0], overwitten by response
    flash_reqmv[0] = 0xA0 # 0xA0 READ STATUS REGISTER
    sdr_response(flash_reqmv[0:2])
    if (flash_reqmv[1] & 0xC1) == 0:
      break
    sleep(0.001)
    retry -= 1
  if retry <= 0:
    print("error flash status 0x%04X & 0xC1 != 0" % (flash_reqmv[1]))

def flash_erase_block(addr=0):
  sdr(b"\x60") # SPI WRITE ENABLE
  # some chips won't clear WIP without this:
  flash_reqmv[0]=0xA0 # READ STATUS
  sdr_response(flash_reqmv[0:2])
  check_response(flash_reqmv[1],mask=0xC1,expected=0x40,message="WRITE ENABLE FAIL")
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_int_msb1st(flash_erase_cmd,0,8)
  send_int_msb1st(addr>>16,0,8)
  send_int_msb1st(addr>>8,0,8)
  send_int_msb1st(addr,1,8) # last byte -> exit 1 DR
  send_tms0111() # -> select DR scan
  flash_wait_status()

def flash_write_block(block, addr=0):
  sdr(b"\x60") # SPI WRITE ENABLE
  send_tms(0) # -> capture DR
  #send_tms(0) # -> shift DR NOTE will be send during TCK glitch
  bitbang_jtag_off() # NOTE TCK glitch
  spi_jtag_on()
  flash_req[0]=2
  flash_req[1]=(addr>>16)&0xFF
  flash_req[2]=(addr>>8)&0xFF
  flash_req[3]=(addr)&0xFF
  jtag.hwspi.write(flash_req)
  jtag.hwspi.write(block[:-1]) # whole block except last byte
  spi_jtag_off()
  bitbang_jtag_on()
  send_int_msb1st(block[-1],1,8) # last byte -> exit 1 DR
  send_tms0111() # -> select DR scan
  flash_wait_status()

# data is bytearray of to-be-read length
def flash_read_block(data, addr=0):
  send_tms(0) # -> capture DR
  #send_tms(0) # -> shift DR NOTE will be sent with bitbang/spi glitch
  bitbang_jtag_off() # NOTE TCK glitch
  spi_jtag_on()
  # 0x03 is SPI flash read command
  flash_req[0]=3
  flash_req[1]=(addr>>16)&0xFF
  flash_req[2]=(addr>>8)&0xFF
  flash_req[3]=(addr)&0xFF
  jtag.hwspi.write(flash_req)
  jtag.hwspi.readinto(data)
  spi_jtag_off()
  bitbang_jtag_on()
  send_int_msb1st(0,1,8) # dummy read byte -> exit 1 DR
  send_tms0111() # -> select DR scan

def flash_close():
  sdr(b"\x20") # SPI WRITE DISABLE
  sir_idle(b"\xFF",100,1) # BYPASS
  sir_idle(b"\x26",2,200) # ISC DISABLE
  sir_idle(b"\xFF",2,1) # BYPASS
  sir(b"\x79") # LSC_REFRESH reload the bitstream from flash
  sdr_idle(b"\x00\x00\x00",2,100)
  reset_tap()
  #led.value=0
  bitbang_jtag_input()
  bitbang_jtag_off()
  bitbang_tms_off()

# data is bytearray of to-be-read length
def flash_read(data, addr=0):
  flash_open()
  flash_read_block(data, addr)
  flash_close()

def compare_flash_file_buf(flash_b, file_b, must:int) -> int:
  flash_block = memoryview(flash_b)
  file_block = memoryview(file_b)
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

def flash_stream(filedata, addr=0):
  addr_mask = flash_erase_size-1
  if addr & addr_mask:
    print("addr must be rounded to flash_erase_size = %d bytes (& 0x%06X)" % (flash_erase_size, 0xFFFFFF & ~addr_mask))
    return
  addr = addr & 0xFFFFFF & ~addr_mask # rounded to even 64K (erase block)
  flash_open()
  bytes_uploaded = 0
  stopwatch_start()
  count_total = 0
  count_erase = 0
  count_write = 0
  file_block = bytearray(flash_erase_size)
  flash_block = bytearray(flash_read_size)
  file_blockmv=memoryview(file_block)
  progress_char="."
  while filedata.readinto(file_block):
    #led.value((bytes_uploaded >> 12)&1)
    retry = 3
    while retry > 0:
      must = 0
      flash_rd = 0
      while flash_rd<flash_erase_size:
        flash_read_block(flash_block,addr+bytes_uploaded+flash_rd)
        must = compare_flash_file_buf(flash_block,file_blockmv[flash_rd:flash_rd+flash_read_size],must)
        flash_rd+=flash_read_size
      write_addr = addr+bytes_uploaded
      if must == 0:
        if (write_addr & 0xFFFF) == 0:
          print("\r0x%06X %dK %c" % (write_addr, flash_erase_size>>10, progress_char),end="")
        else:
          print(progress_char,end="")
        progress_char="."
        count_total += 1
        bytes_uploaded += len(file_block)
        break
      retry -= 1
      if must & 1: # must_erase:
        #print("from 0x%06X erase %dK" % (write_addr, flash_erase_size>>10),end="\r")
        flash_erase_block(write_addr)
        count_erase += 1
        progress_char = "e"
      if must & 2: # must_write:
        #print("from 0x%06X write %dK" % (write_addr, flash_erase_size>>10),end="\r")
        block_addr = 0
        next_block_addr = 0
        while next_block_addr < len(file_block):
          next_block_addr = block_addr+flash_write_size
          flash_write_block(file_blockmv[block_addr:next_block_addr], addr=write_addr)
          write_addr += flash_write_size
          block_addr = next_block_addr
        count_write += 1
        progress_char = "w"
    if retry <= 0:
      break
  print("\r",end="")
  stopwatch_stop(bytes_uploaded)
  print("%dK blocks: %d total, %d erased, %d written." % (flash_erase_size>>10, count_total, count_erase, count_write))
  return retry > 0 # True if successful

def flash(filepath, addr=0, close=True):
  filedata, gz = filedata_gz(filepath)
  if filedata:
    status=flash_stream(filedata,addr)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      flash_close() # start the bitstream
    return status
  return False

def flashrd(addr=0, length=1):
  data = bytearray(length)
  flash_read(data, addr)
  return data
