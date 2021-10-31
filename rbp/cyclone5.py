# micropython ESP32
# CYCLONE5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

# FIXME: esp32 serial line traffic stops after prog()
# TODO: FLASH code not yet implemented, see artix7

from time import ticks_ms, sleep_ms
from machine import SPI, Pin
from micropython import const
from struct import pack, unpack
from uctypes import addressof
from gc import collect

# FJC-ESP32-V0r2 pluggable
#gpio_tms = const(4)
#gpio_tck = const(16)
#gpio_tdi = const(15)
#gpio_tdo = const(2)
#gpio_tcknc = const(21) # 1,2,3,19,21 for SPI workaround
#gpio_led = const(19)
# ESP32-WROVER-E FROGO wired
#gpio_tms = const(5)   # BLUE LED - 549ohm - 3.3V
#gpio_tck = const(18)
#gpio_tdi = const(23)
#gpio_tdo = const(34)
#gpio_tcknc = const(21) # 1,2,3,19,21 for SPI workaround
#gpio_led = const(19)
# ULX3S v3.1.x or FFC-RBP V0r12
gpio_tms = const(5)   # BLUE LED - 549ohm - 3.3V
gpio_tck = const(18)
gpio_tdi = const(23)
gpio_tdo = const(34)
gpio_tcknc = const(21) # 1,2,3,19,21 free pin for SPI workaround
gpio_led = const(19)

spi_freq = const(20000000) # Hz JTAG clk frequency
# -1 for JTAG over SOFT SPI slow, compatibility
#  1 or 2 for JTAG over HARD SPI fast
#  2 is preferred as it has default pinout wired
spi_channel = const(2) # -1 soft, 1:sd, 2:jtag
rb=bytearray(256) # reverse bits
#@micropython.viper
def init_reverse_bits():
  #p8rb=ptr8(addressof(rb))
  p8rb=memoryview(rb)
  for i in range(256):
    v=i
    r=0
    for j in range(8):
      r<<=1
      r|=v&1
      v>>=1
    p8rb[i]=r
init_reverse_bits()
#flash_read_size = const(2048)
#flash_write_size = const(256)
#flash_erase_size = const(4096)
#flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8, 262144:0xD8 } # erase commands from FLASH PDF
#flash_era = bytearray([flash_erase_cmd[flash_erase_size],0,0])
#flash_req=bytearray(4)
#magic=bytearray([0x59,0xA6,0x59,0xA6])
#wrenable=magic+bytearray([0,8,6])
#wrdisable=magic+bytearray([0,8,4])
#read_status=magic+bytearray([0,16,5,0])
status=bytearray(2)
dummy4=bytearray(4)
none=bytearray(0)

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

@micropython.viper
def send_tms(val:int,n:int):
  if val:
    tms.on()
  else:
    tms.off()
  for i in range(n):
    tck.off()
    tck.on()

# TAP should be in IDLE, DRSHIFT, IRSHIFT, DRPAUSE, IRPAUSE state
# TAP stays in the same state
@micropython.viper
def runtest_idle(count:int, duration_ms:int):
  leave=int(ticks_ms()) + duration_ms
  send_tms(0,count) # -> idle
  while int(ticks_ms())-leave < 0:
    send_tms(0,1) # -> idle

def send_tms0110():
  send_tms(0,1) # -> pause DR
  send_tms(1,1) # -> exit 2 DR
  send_tms(1,1) # -> update DR
  send_tms(0,1) # -> idle

def send_tms100():
  send_tms(1,1) # -> select DR scan
  send_tms(0,1) # -> capture DR
  send_tms(0,1) # -> shift DR

@micropython.viper
def send_read_buf_lsb1st(buf, last:int, w:int):
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
    if w:
      p[i] = byte # write byte
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
  if w:
    p[l-1] = byte # write last byte

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
def send_data_int_msb1st(val:int, last:int, bits:int):
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
  send_tms(1,6) # -> Test Logic Reset

# send SIR command (bytes)
# TAP should be in "idle" state
# TAP returns to "exit-IR" state
# LSB first
@micropython.viper
def sir_exit(sir:int)->int:
  send_tms(1,1) # -> select DR scan
  send_tms100() # -> shift IR
  r=int(send_read_int_lsb1st(sir,1,10)) # -> exit 1 IR
  return r

# send SIR command (bytes)
# TAP should be in "idle" state
# TAP returns to "idle" state
# LSB first
@micropython.viper
def sir(ir:int)->int:
  r=int(sir_exit(ir))
  send_tms0110() # -> idle
  return r

# LSB first
@micropython.viper
def sdr(buf):
  send_tms100() # -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms0110() # -> idle

# sdr buffer will be overwritten with response
# LSB first
@micropython.viper
def sdr_response(buf):
  send_tms100() # -> shift DR
  send_read_buf_lsb1st(buf,1,1)
  send_tms0110() # -> idle

# tap in idle and returns to idle
# ir=12 USER0 VDR
# ir=14 USER1 VIR
@micropython.viper
def sir_sdr_int(ir:int,dr:int,bits:int)->int:
  sir_exit(ir) # -> exit-IR
  send_tms(0,12) # -> IRPAUSE
  send_tms(1,2) # -> update-IR
  send_tms100() # -> shift DR
  r=int(send_read_int_lsb1st(dr,1,bits))
  send_tms0110() # -> idle
  return r

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
  send_tms100() # -> shift DR
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
  #  send_data_int_msb1st(byte,0)

def prog_stream_done():
  # switch from hardware SPI to bitbanging done after prog_stream()
  hwspi.init(sck=Pin(gpio_tcknc)) # avoid TCK-glitch
  spi_jtag_off()

# call this after uploading all of the bitstream blocks,
# this will exit FPGA programming mode and start the bitstream
# returns status True-OK False-Fail
def prog_close():
  bitbang_jtag_on()
  send_tms(1,1) # -> exit 1 DR
  send_tms0110() # -> idle
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
  # this is workaround bitstream,
  # without it jtagspi won't load
  file="led%08x.bit.gz" % idcode()
  prog_stream(open_file(file,True))
  if not prog_close():
    print("%s failed" % file)
  file="jtagspi%08x.bit.gz" % idcode()
  prog_stream(open_file(file,True))
  if not prog_close():
    print("%s failed" % file)

# this doesn't work yet
# flash access could be something like this
def flash_id():
  #flash_open()
  common_open()
  bitbang_jtag_on()
  send_tms(1,1) # -> exit 1 DR
  send_tms0110() # -> idle
  runtest_idle(8,2)

  sir_sdr_int(14, 0x1111, 13)
  sir_sdr_int(12,      0,  1)
  sir_sdr_int(14, 0x1FFF, 13)
  sir_sdr_int(14, 0x1A00, 13)
  sir_sdr_int(12,      1,  8)
  sir_sdr_int(14, 0x1002, 13)
  sir_sdr_int(12, rb[0xAB], 40)
  sir_sdr_int(14, 0x1020, 13)
  resp=sir_sdr_int(12, rb[0xAB], 41)

  print("%08X" % (resp & 0xFFFFFFFF))
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

def help():
  print("usage:")
  print("cyclone5.prog(\"http://192.168.4.2/blink.bit\")")
  print("cyclone5.prog(\"blink.bit.gz\") # gzip -9 blink.bit")
  print("\"0x%08X\" % cyclone5.idcode()")
  print("0x%08X" % idcode())

collect()
