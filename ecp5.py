# micropython ESP32
# ECP5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

from time import ticks_ms, sleep_ms
from machine import SPI, SoftSPI, Pin, freq
from micropython import const
from struct import unpack
from uctypes import addressof
from gc import collect
import jtagpin

freq(240000000) # Hz CPU clk frequency
spi_freq = const(20000000) # Hz JTAG clk frequency
flash_read_size = const(2048)
flash_write_size = const(256)
flash_erase_size = const(4096)
flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8, 262144:0xD8 } # erase commands from FLASH PDF
flash_era = bytearray([flash_erase_cmd[flash_erase_size],0,0])
flash_req=bytearray(4)
read_status=bytearray([5])
status=bytearray(1)
#rb=bytearray(256) # reverse bits
#init_reverse_bits()

def bitbang_jtag_on():
  global tck,tms,tdi,tdo,led
  led=Pin(jtagpin.led,Pin.OUT)
  tms=Pin(jtagpin.tms,Pin.OUT)
  tck=Pin(jtagpin.tck,Pin.OUT)
  tdi=Pin(jtagpin.tdi,Pin.OUT)
  tdo=Pin(jtagpin.tdo,Pin.IN)

def bitbang_jtag_off():
  global tck,tms,tdi,tdo,led
  led=Pin(jtagpin.led,Pin.IN)
  tms=Pin(jtagpin.tms,Pin.IN)
  tck=Pin(jtagpin.tck,Pin.IN)
  tdi=Pin(jtagpin.tdi,Pin.IN)
  tdo=Pin(jtagpin.tdo,Pin.IN)
  a = led.value()
  a = tms.value()
  a = tck.value()
  a = tdo.value()
  a = tdi.value()
  del led
  del tms
  del tck
  del tdi
  del tdo

# initialize both hardware accelerated SPI
# software SPI on the same pins
def spi_jtag_on():
  global hwspi,swspi
  try: # ESP32 classic
    hwspi=SPI(2, baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(jtagpin.tck), mosi=Pin(jtagpin.tdi), miso=Pin(jtagpin.tdo))
  except: # ESP32-S2
    hwspi=SPI(baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(jtagpin.tck), mosi=Pin(jtagpin.tdi), miso=Pin(jtagpin.tdo))
  swspi=SoftSPI(baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(jtagpin.tck), mosi=Pin(jtagpin.tdi), miso=Pin(jtagpin.tdo))

def spi_jtag_off():
  global hwspi,swspi
  hwspi.deinit()
  del hwspi
  swspi.deinit()
  del swspi

# print bytes reverse - appears the same as in SVF file
#def print_hex_reverse(block, head="", tail="\n"):
#  print(head, end="")
#  for n in range(len(block)):
#    print("%02X" % block[len(block)-n-1], end="")
#  print(tail, end="")

#@micropython.viper
#def init_reverse_bits():
#  #p8rb=ptr8(addressof(rb))
#  p8rb=memoryview(rb)
#  for i in range(256):
#    v=i
#    r=0
#    for j in range(8):
#      r<<=1
#      r|=v&1
#      v>>=1
#    p8rb[i]=r

@micropython.viper
def send_tms(val:int,n:int):
  if val:
    tms.on()
  else:
    tms.off()
  for i in range(n):
    tck.off()
    tck.on()

# exit 1 DR -> select DR scan
def send_tms0111():
  send_tms(0,1) # -> pause DR
  send_tms(1,3) # -> exit 2 DR -> update DR -> select DR scan

@micropython.viper
def send_read_buf_lsb1st(buf, last:int, w:ptr8):
  p = ptr8(addressof(buf))
  l = int(len(buf))
  val = 0
  tms.off()
  for i in range(l-1):
    byte = 0
    val = p[i]
    for nf in range(8):
      if (val >> nf) & 1:
        tdi.on()
      else:
        tdi.off()
      tck.off()
      tck.on()
      if tdo.value():
        byte |= 1 << nf
    if int(w):
      w[i] = byte # write byte
  byte = 0
  val = p[l-1] # read last byte
  for nf in range(7): # first 7 bits
    if (val >> nf) & 1:
      tdi.on()
    else:
      tdi.off()
    tck.off()
    tck.on()
    if tdo.value():
      byte |= 1 << nf
  # last bit
  if last:
    tms.on()
  if (val >> 7) & 1:
    tdi.on()
  else:
    tdi.off()
  tck.off()
  tck.on()
  if tdo.value():
    byte |= 1 << 7
  if int(w):
    w[l-1] = byte # write last byte

@micropython.viper
def send_int_msb1st(val:int, last:int, bits:int):
  tms.off()
  for nf in range(bits-1):
    if (val >> (7-nf)) & 1:
      tdi.on()
    else:
      tdi.off()
    tck.off()
    tck.on()
  if last:
    tms.on()
  if val & 1:
    tdi.on()
  else:
    tdi.off()
  tck.off()
  tck.on()

# TAP should be in "idle" state
# TAP returns to "select DR scan" state
@micropython.viper
def runtest_idle(count:int, duration_ms:int):
  leave=int(ticks_ms()) + duration_ms
  send_tms(0,count) # -> idle
  while int(ticks_ms())-leave < 0:
    send_tms(0,1) # -> idle
  send_tms(1,1) # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
@micropython.viper
def sir(buf):
  send_tms(1,1) # -> select IR scan
  send_tms(0,2) # -> capture IR -> shift IR
  send_read_buf_lsb1st(buf,1,0) # -> exit 1 IR
  send_tms0111() # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
# finish with n idle cycles during minimum of ms time
@micropython.viper
def sir_idle(buf, n:int, ms:int):
  send_tms(1,1) # -> select IR scan
  send_tms(0,2) # -> capture IR -> shift IR
  send_read_buf_lsb1st(buf,1,0) # -> exit 1 IR
  send_tms(0,1) # -> pause IR
  send_tms(1,2) # -> exit 2 IR -> update IR
  runtest_idle(n+1,ms) # -> select DR scan

@micropython.viper
def sdr(buf):
  send_tms(0,2) # -> capture DR -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms0111() # -> select DR scan

@micropython.viper
def sdr_idle(buf, n:int, ms:int):
  send_tms(0,2) # -> capture DR -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms(0,1) # -> pause IR
  send_tms(1,2) # -> exit 2 IR -> update IR
  runtest_idle(n+1, ms) # -> select DR scan

# sdr buffer will be overwritten with response
@micropython.viper
def sdr_response(buf):
  send_tms(0,2) # -> capture DR -> shift DR
  send_read_buf_lsb1st(buf,1,addressof(buf))
  send_tms0111() # -> select DR scan

def check_response(response, expected, mask=0xFFFFFFFF, message=""):
  if (response & mask) != expected:
    print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

def idcode():
  bitbang_jtag_on()
  led.on()
  send_tms(1,6) # -> Test Logic Reset
  runtest_idle(1,0)
  #sir(b"\xE0")
  id_bytes = bytearray(4)
  sdr_response(id_bytes)
  led.off()
  bitbang_jtag_off()
  return unpack("<I", id_bytes)[0]

# common JTAG open for both program and flash
def common_open():
  spi_jtag_on()
  hwspi.init(sck=Pin(jtagpin.tcknc)) # avoid TCK-glitch
  bitbang_jtag_on()
  led.on()
  send_tms(1,6) # -> Test Logic Reset
  runtest_idle(1,0)
  #sir(b"\xE0") # read IDCODE
  #sdr(pack("<I",0), expected=pack("<I",0), message="IDCODE")
  sir(b"\x1C") # LSC_PRELOAD: program Bscan register
  sdr(bytearray([0xFF for i in range(64)]))
  sir(b"\xC6") # ISC ENABLE: Enable SRAM programming mode
  sdr_idle(b"\x00",2,10)
  sir_idle(b"\x3C",2,1) # LSC_READ_STATUS
  status = bytearray(4)
  sdr_response(status)
  check_response(unpack("<I",status)[0], mask=0x24040, expected=0, message="FAIL status")
  sir(b"\x0E") # ISC_ERASE: Erase the SRAM
  sdr_idle(b"\x01",2,10)
  sir_idle(b"\x3C",2,1) # LSC_READ_STATUS
  status = bytearray(4)
  sdr_response(status)
  check_response(unpack("<I",status)[0], mask=0xB000, expected=0, message="FAIL status")

# call this before sending the bitstram
# FPGA will enter programming mode
# after this TAP will be in "shift DR" state
def prog_open():
  common_open()
  sir(b"\x46") # LSC_INIT_ADDRESS
  sdr_idle(b"\x01",2,10)
  sir(b"\x7A") # LSC_BITSTREAM_BURST
  # ---------- bitstream begin -----------
  # manually walk the TAP
  # we will be sending one long DR command
  send_tms(0,2) # -> capture DR -> shift DR
  # switch from bitbanging to SPI mode
  hwspi.init(sck=Pin(jtagpin.tck)) # 1 TCK-glitch? TDI=0
  # we are lucky that format of the bitstream tolerates
  # any leading and trailing junk bits. If it weren't so,
  # HW SPI JTAG acceleration wouldn't work.
  # to upload the bitstream:
  # FAST SPI mode
  #hwspi.write(block)
  # SLOW bitbanging mode
  #for byte in block:
  #  send_int_msb1st(byte,0)

def prog_stream_done():
  # switch from hardware SPI to bitbanging done after prog_stream()
  hwspi.init(sck=Pin(jtagpin.tcknc)) # avoid TCK-glitch
  spi_jtag_off()

# call this after uploading all of the bitstream blocks,
# this will exit FPGA programming mode and start the bitstream
# returns status True-OK False-Fail
def prog_close():
  bitbang_jtag_on()
  send_tms(1,1) # -> exit 1 DR
  send_tms(0,1) # -> pause DR
  send_tms(1,2) # -> exit 2 DR -> update DR
  #send_tms(0,1) # -> idle, disabled here as runtest_idle does the same
  runtest_idle(100,10)
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
  send_tms(1,6) # -> Test Logic Reset
  led.off()
  bitbang_jtag_off()
  return done

# call this before sending the flash image
# FPGA will enter flashing mode
# TAP should be in "select DR scan" state
def flash_open():
  common_open()
  send_tms(1,6) # -> Test Logic Reset
  runtest_idle(1,0)
  sir_idle(b"\xFF",32,0) # BYPASS
  sir(b"\x3A") # LSC_PROG_SPI
  sdr_idle(b"\xFE\x68",32,0)
  # ---------- flashing begin -----------
  # sdr("\x60") and other SPI FLASH commands
  # here are bitreverse() values of FLASH commands
  # found in datasheet. e.g.
  # \x1B -> 0xD8
  # \x60 -> 0x06 ...

@micropython.viper
def flash_wait_status(n:int):
  retry=n
  mask=1 # WIP bit (work-in-progress)
  send_tms(0,2) # -> capture DR -> shift DR
  swspi.write(read_status) # READ STATUS REGISTER
  swspi.readinto(status)
  while retry > 0:
    swspi.readinto(status)
    if (int(status[0]) & mask) == 0:
      break
    sleep_ms(1)
    retry -= 1
  send_tms(1,1) # -> exit 1 DR # exit at byte incomplete
  #send_int_msb1st(0,1,8) # exit at byte complete
  send_tms0111() # -> select DR scan
  if retry <= 0:
    print("error %d flash status 0x%02X & 0x%02X != 0" % (n,status[0],mask))

@micropython.viper
def flash_erase_block(addr:int):
  sdr(b"\x60") # SPI WRITE ENABLE
  flash_wait_status(1001)
  p8=ptr8(addressof(flash_era))
  p8[1]=addr>>16
  p8[2]=addr>>8
  send_tms(0,2) # -> capture DR -> shift DR
  swspi.write(flash_era) # except LSB
  send_int_msb1st(addr,1,8) # last LSB byte -> exit 1 DR
  send_tms0111() # -> select DR scan
  flash_wait_status(2002)

@micropython.viper
def flash_write_block(block, last:int, addr:int):
  sdr(b"\x60") # SPI WRITE ENABLE
  flash_wait_status(1003)
  p8=ptr8(addressof(flash_req))
  p8[0]=2
  p8[1]=addr>>16
  p8[2]=addr>>8
  p8[3]=addr
  send_tms(0,2) # -> capture DR -> shift DR
  swspi.write(flash_req)
  swspi.write(block) # whole block
  send_int_msb1st(last,1,8) # last byte -> exit 1 DR
  send_tms0111() # -> select DR scan
  flash_wait_status(1004)

# data is bytearray of to-be-read length
@micropython.viper
def flash_read_block(data, addr:int):
  p8=ptr8(addressof(flash_req))
  p8[0]=3
  p8[1]=addr>>16
  p8[2]=addr>>8
  p8[3]=addr
  send_tms(0,2) # -> capture DR -> shift DR
  swspi.write(flash_req) # send SPI FLASH read command and address and dummy byte
  swspi.readinto(data) # retrieve whole block
  send_int_msb1st(0,1,8) # dummy read byte -> exit 1 DR
  send_tms0111() # -> select DR scan

# call this after uploading all of the flash blocks,
# this will exit FPGA flashing mode and start the bitstream
def flash_close():
  # switch from SPI to bitbanging
  # ---------- flashing end -----------
  sdr(b"\x20") # SPI WRITE DISABLE
  sir_idle(b"\xFF",100,1) # BYPASS
  sir_idle(b"\x26",2,200) # ISC DISABLE
  sir_idle(b"\xFF",2,1) # BYPASS
  sir(b"\x79") # LSC_REFRESH reload the bitstream from flash
  sdr_idle(b"\x00\x00\x00",2,100)
  spi_jtag_off()
  send_tms(1,6) # -> Test Logic Reset
  led.off()
  bitbang_jtag_off()

def stopwatch_start():
  global stopwatch_ms
  stopwatch_ms = ticks_ms()

def stopwatch_stop(bytes_uploaded):
  global stopwatch_ms
  elapsed_ms = ticks_ms() - stopwatch_ms
  transfer_rate_MBps = 0
  if elapsed_ms > 0:
    transfer_rate_kBps = bytes_uploaded // elapsed_ms
  print("%d bytes uploaded in %d ms (%d kB/s)" % (bytes_uploaded, elapsed_ms, transfer_rate_kBps))

def prog_stream(dstream, blocksize=4096):
  prog_open()
  bytes_uploaded = 0
  stopwatch_start()
  block = bytearray(blocksize)
  while True:
    if dstream.readinto(block):
      hwspi.write(block)
      bytes_uploaded += len(block)
    else:
      break
  stopwatch_stop(bytes_uploaded)
  prog_stream_done()

def prog_stream_gz(dstream, blocksize=4096, name=""):
  if name.lower().endswith(".gz"):
    import uzlib
    prog_stream(uzlib.DecompIO(dstream,31), blocksize)
  else:
    prog_stream(dstream, blocksize)

def open_web(url):
  import socket
  _, _, host, path = url.split('/', 3)
  port = 80
  if ( len(host.split(':')) == 2 ):
    host, port = host.split(':', 2)
    port = int(port)
  print("host = %s, port = %d, path = %s" % (host, port, path))
  addr = socket.getaddrinfo(host, port)[0][-1]
  s = socket.socket()
  s.connect(addr)
  s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\nAccept:  image/*\r\n\r\n' % (path, host), 'utf8'))
  for i in range(100): # read first 100 lines searching for
    if len(s.readline()) < 3: # first empty line (contains "\r\n")
      break
  return s

# data is bytearray of to-be-read length
def flash_read(data, addr=0):
  flash_open()
  flash_read_block(data, addr)
  flash_close()

# accelerated compare flash and file block
# return value
# 0-must nothing, 1-must erase, 2-must write, 3-must erase and write
@micropython.viper
def compare_flash_file_buf(flash_b, file_b, must:int)->int:
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
# 4K erase block is max that fits on ESP32-WROOM
# returns status True-OK False-Fail
def flash_stream(dstream, addr=0):
  flash_open()
  addr_mask = flash_erase_size-1
  if addr & addr_mask:
    print("addr must be rounded to flash_erase_size = %d bytes (& 0x%06X)" % (flash_erase_size, 0xFFFFFF & ~addr_mask))
    return False
  addr = addr & 0xFFFFFF & ~addr_mask # rounded to even 64K (erase block)
  bytes_uploaded = 0
  stopwatch_start()
  #if 1:
  #  print("erase whole FLASH (max 90s)")
  #  sdr(b"\x60") # SPI WRITE ENABLE
  #  flash_wait_status(1005)
  #  sdr(b"\xE3") # BULK ERASE (whole chip) rb[0x60]=0x06 or rb[0xC7]=0xE3
  #  flash_wait_status(90000)
  count_total = 0
  count_erase = 0
  count_write = 0
  file_block = bytearray(flash_erase_size)
  flash_block = bytearray(flash_read_size)
  file_blockmv=memoryview(file_block)
  progress_char="."
  while dstream.readinto(file_block):
    led.value((bytes_uploaded >> 12)&1)
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
          flash_write_block(file_blockmv[block_addr:next_block_addr-1], file_blockmv[next_block_addr-1], write_addr)
          write_addr += flash_write_size
          block_addr = next_block_addr
        count_write += 1
        progress_char = "w"
      #if not verify:
      #  count_total += 1
      #  bytes_uploaded += len(file_block)
      #  break
    if retry <= 0:
      break
  print("\r",end="")
  stopwatch_stop(bytes_uploaded)
  print("%dK blocks: %d total, %d erased, %d written." % (flash_erase_size>>10, count_total, count_erase, count_write))
  return retry > 0 # True if successful

def flash_stream_gz(dstream, addr=0, name=""):
  if name.lower().endswith(".gz"):
    import uzlib
    flash_stream(uzlib.DecompIO(dstream,31), addr)
  else:
    flash_stream(dstream, addr)

def datastream(filepath):
  if filepath.startswith("http://") or filepath.startswith("/http:/"):
    return open_web(filepath)
  else:
    return open(filepath, "rb")

def prog(filepath, close=True):
  collect()
  dstream = datastream(filepath)
  if dstream:
    prog_stream_gz(dstream,4096,filepath)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      return prog_close() # start the bitstream
    return True
  return False

def flash(filepath, addr=0, close=True):
  collect()
  dstream = datastream(filepath)
  if dstream:
    status=flash_stream_gz(dstream,addr,filepath)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      flash_close() # start the bitstream
    return status
  return False

def flashrd(addr=0, length=1):
  collect()
  data = bytearray(length)
  flash_read(data, addr)
  return data

def passthru():
  collect()
  id = idcode()
  if id != 0 and id != 0xFFFFFFFF:
    filepath = "passthru%08x.bit.gz" % id
    print("ecp5.prog(\"%s\")" % filepath)
    dstream = datastream(filepath)
    prog_stream_gz(dstream,4096,filepath)
    return prog_close()
  return False

def help():
  print("usage:")
  print("ecp5.flash(\"blink.bit.gz\", addr=0x000000)")
  print("ecp5.flashrd(addr=0x000000, length=1)")
  print("ecp5.prog(\"http://192.168.4.2/blink.bit\")")
  print("ecp5.prog(\"blink.bit.gz\") # gzip -9 blink.bit")
  print("ecp5.passthru()")
  print("\"0x%08X\" % ecp5.idcode()")
  print("0x%08X" % idcode())
