# micropython ESP32
# CYCLONE5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

# NOTE: replace FLASH code for artix7 with code for cyclone5

from time import ticks_ms, sleep_ms
from machine import SPI, Pin
from micropython import const
from struct import pack, unpack
from uctypes import addressof
from gc import collect

spi_freq = const(25000000) # Hz JTAG clk frequency
# -1 for JTAG over SOFT SPI slow, compatibility
#  1 or 2 for JTAG over HARD SPI fast
#  2 is preferred as it has default pinout wired
flash_read_size = const(2048)
flash_write_size = const(256)
flash_erase_size = const(4096) # WROOM
#flash_erase_size = const(65536) # WROVER
flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8 } # erase commands from FLASH PDF
flash_erase_cmd = flash_erase_cmd[flash_erase_size]
#rb=bytearray(256) # reverse bits
#init_reverse_bits()
spi_channel = const(2) # -1 soft, 1:sd, 2:jtag
magic=bytearray([0x59,0xA6,0x59,0xA6])
wrenable=magic+bytearray([0,8,6])
wrdisable=magic+bytearray([0,8,4])
read_status=magic+bytearray([0,16,5,0])
status=bytearray(2)
dummy4=bytearray(4)
none=bytearray(0)

# FJC-ESP32-V0r2 pluggable
#gpio_tms = const(4)
#gpio_tck = const(16)
#gpio_tdi = const(15)
#gpio_tdo = const(2)
#gpio_tcknc = const(21) # 1,2,3,19,21 for SPI workaround
#gpio_led = const(19)
# ESP32-WROVER-E FROGO wired
gpio_tms = const(5)   # BLUE LED - 549ohm - 3.3V
gpio_tck = const(18)
gpio_tdi = const(23)
gpio_tdo = const(34)
gpio_tcknc = const(21) # 1,2,3,19,21 for SPI workaround
gpio_led = const(19)

def bitbang_jtag_on():
  global tck,tms,tdi,tdo,led
  led=Pin(gpio_led,Pin.OUT)
  tms=Pin(gpio_tms,Pin.OUT)
  tck=Pin(gpio_tck,Pin.OUT)
  tdi=Pin(gpio_tdi,Pin.OUT)
  tdo=Pin(gpio_tdo,Pin.IN)

def bitbang_jtag_off():
  global tck,tms,tdi,tdo,led
  led=Pin(gpio_led,Pin.IN)
  tms=Pin(gpio_tms,Pin.IN)
  tck=Pin(gpio_tck,Pin.IN)
  tdi=Pin(gpio_tdi,Pin.IN)
  tdo=Pin(gpio_tdo,Pin.IN)
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
  hwspi=SPI(spi_channel, baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(gpio_tck), mosi=Pin(gpio_tdi), miso=Pin(gpio_tdo))
  swspi=SPI(-1, baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(gpio_tck), mosi=Pin(gpio_tdi), miso=Pin(gpio_tdo))

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
#  p8rb=ptr8(addressof(rb))
#  #p8rb=memoryview(rb)
#  for i in range(256):
#    v=i
#    r=0
#    for j in range(8):
#      r<<=1
#      r|=v&1
#      v>>=1
#    p8rb[i]=r

#@micropython.viper
#def reverse_bits(b,l:int):
#  p8=ptr8(addressof(b))
#  p8rb=ptr8(addressof(rb))
#  for i in range(l):
#    p8[i]=p8rb[p8[i]]

@micropython.viper
def send_tms(val:int):
  if val:
    tms.on()
  else:
    tms.off()
  tck.off()
  tck.on()

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
def send_read_int_lsb1st(val:int, last:int, bits:int)->int:
  tms.off()
  byte = 0
  for nf in range(bits-1):
    if (val >> nf) & 1:
      tdi.on()
    else:
      tdi.off()
    tck.off()
    tck.on()
    if tdo.value():
      byte |= 1 << nf
  if last:
    tms.on()
  if (val >> (bits-1)) & 1:
    tdi.on()
  else:
    tdi.off()
  tck.off()
  tck.on()
  if tdo.value():
    byte |= 1 << (bits-1)
  return byte

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
  
# TAP to "reset" state
@micropython.viper
def reset_tap():
  for n in range(6):
    send_tms(1) # -> Test Logic Reset

# TAP should be in "idle" state
# TAP returns to "idle" state
@micropython.viper
def runtest_idle(count:int, duration_ms:int):
  leave=int(ticks_ms()) + duration_ms
  for n in range(count):
    send_tms(0) # -> idle
  while int(ticks_ms()) < leave:
    send_tms(0) # -> idle

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
# LSB first
@micropython.viper
def sir(sir:int)->int:
  send_tms(1) # -> select DR scan
  send_tms(1) # -> select IR scan
  send_tms(0) # -> capture IR
  send_tms(0) # -> shift IR
  r=int(send_read_int_lsb1st(sir,1,10)) # -> exit 1 IR
  send_tms(0) # -> pause IR
  send_tms(1) # -> exit 2 IR
  send_tms(1) # -> update IR
  send_tms(0) # -> idle
  return r

# LSB first
@micropython.viper
def sdr(buf):
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(0) # -> idle

# sdr buffer will be overwritten with response
# LSB first
@micropython.viper
def sdr_response(buf):
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(buf,1,addressof(buf))
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(0) # -> idle

# USER1 send a+b MSB first
# a can be 0-size
def user1_send(a,b):
  sir(2) # USER1
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  swspi.write(a)
  swspi.write(b[:-1])
  send_int_msb1st(b[-1],1,8) # last byte -> exit 1 DR
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(0) # -> idle

# USER1 send a, recv b
# a can be 0-size
# after b, it reads one dummy bit
@micropython.viper
def user1_send_recv(a,b):
  sir(2) # USER1
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  swspi.write(a)
  swspi.readinto(b)
  send_tms(1) # -> exit 1 DR, dummy bit
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(0) # -> idle

def check_response(response, expected, mask=0xFFFFFFFF, message=""):
  if (response & mask) != expected:
    print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

def idcode():
  bitbang_jtag_on()
  led.on()
  reset_tap()
  runtest_idle(1,0)
  #sir(6)
  id_bytes = bytearray(4)
  sdr_response(id_bytes)
  led.off()
  bitbang_jtag_off()
  return unpack("<I", id_bytes)[0]

# common JTAG open for both program and flash
def common_open():
  spi_jtag_on()
  hwspi.init(sck=Pin(gpio_tcknc)) # avoid TCK-glitch
  bitbang_jtag_on()
  led.on()
  reset_tap()
  runtest_idle(1,0)

# call this before sending the bitstram
# FPGA will enter programming mode
# after this TAP will be in "shift DR" state
def prog_open():
  common_open()
  sir(2)
  runtest_idle(8,2)
  # ---------- bitstream begin -----------
  # manually walk the TAP
  # we will be sending one long DR command
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR # NOTE sent with 1 TCK glitch
  # switch from bitbanging to SPI mode
  hwspi.init(sck=Pin(gpio_tck)) # 1 TCK-glitch TDI=0
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
  hwspi.init(sck=Pin(gpio_tcknc)) # avoid TCK-glitch
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
  send_tms(0) # -> idle
  runtest_idle(8,2)
  # ---------- bitstream end -----------
  sir(4)
  runtest_idle(165,0)
  errors=bytearray(108)
  sdr_response(errors)
  ok = (errors[20]&8)==8
  sir(3)
  runtest_idle(8,6)
  sir(0x3FF) # BYPASS
  runtest_idle(8,2)
  reset_tap()
  led.off()
  bitbang_jtag_off()
  return ok

# call this before sending the flash image
# FPGA will enter flashing mode
# TAP should be in "select DR scan" state
@micropython.viper
def flash_open():
  prog_stream(open_file("bscan7.bit.gz",True))
  if not prog_close():
    print("bscan7.bit.gz failed")
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

def prog_stream(filedata, blocksize=16384):
  prog_open()
  bytes_uploaded = 0
  stopwatch_start()
  block = bytearray(blocksize)
  while True:
    if filedata.readinto(block):
      #reverse_bits(block,blocksize)
      hwspi.write(block)
      bytes_uploaded += len(block)
    else:
      break
  stopwatch_stop(bytes_uploaded)
  prog_stream_done()

def open_file(filename, gz=False):
  filedata = open(filename, "rb")
  if gz:
    import uzlib
    return uzlib.DecompIO(filedata,31)
  return filedata

def open_web(url, gz=False):
  import socket
  _, _, host, path = url.split('/', 3)
  port = 80
  if ( len(host.split(':')) == 2 ):
    host, port = host.split(':', 2)
  print("host = %s, port = %d, path = %s" % (host, port, path))
  addr = socket.getaddrinfo(host, port)[0][-1]
  s = socket.socket()
  s.connect(addr)
  s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\nAccept:  image/*\r\n\r\n' % (path, host), 'utf8'))
  for i in range(100): # read first 100 lines searching for
    if len(s.readline()) < 3: # first empty line (contains "\r\n")
      break
  if gz:
    import uzlib
    return uzlib.DecompIO(s,31)
  return s

# data is bytearray of to-be-read length
def flash_readinto(data, addr=0):
  flash_open()
  flash_read_block(data, addr)
  flash_close()

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
# TODO reduce buffer usage
# returns status True-OK False-Fail
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
  progress_char="."
  while filedata.readinto(file_block):
    led.value((bytes_uploaded >> 12)&1)
    retry = 3
    while retry >= 0:
      must = 0
      flash_rd = 0
      while flash_rd<flash_erase_size:
        flash_read_block(flash_block,addr+bytes_uploaded+flash_rd)
        must = compare_flash_file_buf(flash_block,file_block[flash_rd:flash_rd+flash_read_size],must)
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
          flash_write_block(file_block[block_addr:next_block_addr], addr=write_addr)
          write_addr += flash_write_size
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
  print("%dK blocks: %d total, %d erased, %d written." % (flash_erase_size>>10, count_total, count_erase, count_write))
  return retry >= 0 # True if successful

def filedata_gz(filepath):
  gz = filepath.endswith(".gz")
  if filepath.startswith("http://") or filepath.startswith("/http:/"):
    filedata = open_web(filepath, gz)
  else:
    filedata = open_file(filepath, gz)
  return filedata, gz

def prog(filepath, close=True):
  filedata, gz = filedata_gz(filepath)
  if filedata:
    if gz:
      prog_stream(filedata,blocksize=4096)
    else:
      prog_stream(filedata,blocksize=16384)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      return prog_close() # start the bitstream
    return True
  return False

def flash(filepath, addr=0, close=True):
  filedata, gz = filedata_gz(filepath)
  if filedata:
    status=flash_stream(filedata,addr)
    # NOTE now the SD card can be released before bitstream starts
    if close:
      flash_close() # start the bitstream
    return status
  return False

def flash_read(addr=0, length=1):
  data = bytearray(length)
  cyclone5().flash_readinto(data, addr)
  return data

def help():
  print("usage:")
  print("cyclone5.flash(\"blink.bit.gz\", addr=0x000000)")
  print("cyclone5.flash_read(addr=0x000000, length=1)")
  print("cyclone5.prog(\"http://192.168.4.2/blink.bit\")")
  print("cyclone5.prog(\"blink.bit.gz\") # gzip -9 blink.bit")
  print("\"0x%08X\" % cyclone5.idcode()")
  print("0x%08X" % idcode())
