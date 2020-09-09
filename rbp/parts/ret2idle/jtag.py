# micropython ESP32
# JTAG common functions

# AUTHOR=EMARD
# LICENSE=BSD

from time import ticks_ms
from machine import SPI, Pin
from micropython import const
from uctypes import addressof

# FIXME hi-z tcknc

# FJC-ESP32-V0r2 pluggable
#gpio_tms = const(4)
#gpio_tck = const(16)
#gpio_tdi = const(15)
#gpio_tdo = const(2)
#gpio_tcknc = const(21)
#gpio_led = const(19)
# ULX3S v3.1.x and ESP32-WROVER-E FROGO wired
gpio_tms = const(5)   # BLUE LED - 549ohm - 3.3V
gpio_tck = const(18)
gpio_tdi = const(23)
gpio_tdo = const(34)
gpio_tcknc = const(21) # 1,2,3,19,21 for SPI workaround
gpio_led = const(19)
# ULX3S v3.0.x
#gpio_tms = const(21)
#gpio_tck = const(18)
#gpio_tdi = const(23)
#gpio_tdo = const(19)
#gpio_tcknc = const(17) # free pin for SPI workaround
#gpio_led = const(5)

irlen = 8
spi_freq = const(25000000) # Hz JTAG clk frequency
spi_channel = const(2) # -1 soft, 1:sd, 2:jtag

hwspi=None
swspi=None

def bitbang_jtag_on():
  global tms,tck,tdi,tdo,led
  led=Pin(gpio_led,Pin.OUT)
  tms=Pin(gpio_tms,Pin.OUT)
  tck=Pin(gpio_tck,Pin.OUT)
  tdi=Pin(gpio_tdi,Pin.OUT)
  tdo=Pin(gpio_tdo,Pin.IN)

def bitbang_jtag_off():
  global tms,tck,tdi,tdo,led
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
#def print_hex_reverse(self, block, head="", tail="\n"):
#  print(head, end="")
#  for n in range(len(block)):
#    print("%02X" % block[len(block)-n-1], end="")
#  print(tail, end="")

#@micropython.viper
#def init_reverse_bits(self):
#  p8rb=ptr8(addressof(self.rb))
#  #p8rb=memoryview(self.rb)
#  for i in range(256):
#    v=i
#    r=0
#    for j in range(8):
#      r<<=1
#      r|=v&1
#      v>>=1
#    p8rb[i]=r

@micropython.viper
def send_tms(val:int):
  if val:
    tms.on()
  else:
    tms.off()
  tck.off()
  tck.on()

@micropython.viper
def send_read_data_buf(buf, last:int, w:ptr8):
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
def send_read_data_byte(val:int, last:int, bits:int)->int:
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
def send_data_byte_reverse(val:int, last:int, bits:int):
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
# TAP returns to "select DR scan" state
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
def sir(val:int)->int:
  send_tms(1) # -> select DR scan
  send_tms(1) # -> select IR scan
  send_tms(0) # -> capture IR
  send_tms(0) # -> shift IR
  r=int(send_read_data_byte(val,1,irlen)) # -> exit 1 IR
  send_tms(0) # -> pause IR
  send_tms(1) # -> exit 2 IR
  send_tms(1) # -> update IR
  send_tms(0) # -> idle
  return r

@micropython.viper
def sir_idle(val:int, n:int, ms:int)->int:
  send_tms(1) # -> select DR scan
  send_tms(1) # -> select IR scan
  send_tms(0) # -> capture IR
  send_tms(0) # -> shift IR
  r=int(send_read_data_byte(val,1,irlen)) # -> exit 1 IR
  send_tms(0) # -> pause IR
  send_tms(1) # -> exit 2 IR
  send_tms(1) # -> update IR
  runtest_idle(n+1, ms) # -> idle
  return r

# LSB first
@micropython.viper
def sdr(buf):
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_data_buf(buf,1,0)
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(0) # -> idle

# LSB first
@micropython.viper
def sdr_idle(buf, n:int, ms:int):
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_data_buf(buf,1,0)
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  runtest_idle(n+1, ms) # -> idle

# sdr buffer will be overwritten with response LSB first
@micropython.viper
def sdr_response(buf):
  send_tms(1) # -> select DR scan
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_data_buf(buf,1,addressof(buf))
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(0) # -> idle

# common JTAG open for both program and flash
def jtag_open():
  spi_jtag_on()
  hwspi.init(sck=Pin(gpio_tcknc)) # avoid TCK-glitch
  bitbang_jtag_on()
  led.on()
  reset_tap()
  runtest_idle(1,0)

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

def open_file(filename, gz=False):
  filedata = open(filename,"rb")
  if gz:
    import uzlib
    return uzlib.DecompIO(filedata,31)
  return filedata

def open_web(url, gz=False):
  import socket
  _, _, host, path = url.split('/',3)
  port = 80
  if ( len(host.split(':')) == 2 ):
    host, port = host.split(':',2)
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

def check_response(response, expected, mask=0xFFFFFFFF, message=""):
  if (response & mask) != expected:
    print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))
