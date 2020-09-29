# circuitpython ESP32S2
# ECP5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

from time import sleep, monotonic_ns
import board, busio, digitalio
from micropython import const
from struct import pack, unpack

#gpio_tdi = board.IO11
#gpio_tck = board.IO12
#gpio_tdo = board.IO13
#gpio_tms = board.IO14  # BLUE LED - 549ohm - 3.3V
gpio_tdi = board.IO35
gpio_tck = board.IO36
gpio_tdo = board.IO37
gpio_tms = board.IO38  # BLUE LED - 549ohm - 3.3V

spi_freq = const(40000000) # Hz JTAG clk frequency
hwspi=None


def bitbang_tms_on():
  global tms
  tms=digitalio.DigitalInOut(gpio_tms)
  tms.direction=digitalio.Direction.OUTPUT

def bitbang_tms_off():
  global tms
  tms.deinit()
  #del tms

def bitbang_jtag_on():
  global tck,tdo,tdi
  tck=digitalio.DigitalInOut(gpio_tck)
  tdi=digitalio.DigitalInOut(gpio_tdi)
  tdo=digitalio.DigitalInOut(gpio_tdo)
  tck.switch_to_output(value=True)
  tdi.switch_to_output(value=True)
  tdo.switch_to_input()

def bitbang_jtag_off():
  global tck,tdo,tdi
  #tck.switch_to_input(pull=digitalio.Pull.UP)
  #tdo.switch_to_input(pull=digitalio.Pull.UP)
  #tdi.switch_to_input(pull=digitalio.Pull.UP)
  tck.deinit()
  tdo.deinit()
  tdi.deinit()
  #del tck,tdo,tdi

def bitbang_jtag_input():
  tck.switch_to_input(pull=None)
  tms.switch_to_input(pull=None)
  tdi.switch_to_input(pull=None)
  tdo.switch_to_input(pull=None)

def spi_jtag_on():
  global hwspi
  hwspi=busio.SPI(clock=gpio_tck,MOSI=gpio_tdi,MISO=gpio_tdo)
  while not hwspi.try_lock():
    pass
  hwspi.configure(baudrate=spi_freq,polarity=1,phase=1)

def spi_jtag_off():
  global hwspi
  hwspi.deinit()
  del hwspi

def send_tms(val:int):
  #global tms,tck
  tms.value=val
  tck.value=0
  tck.value=1

# exit 1 DR -> select DR scan
def send_tms0111():
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan

def send_read_buf_lsb1st(buf, last:int, w):
  #global tck,tms,tdi,tdo
  p = memoryview(buf)
  l = int(len(buf))
  val = 0
  tms.value=0
  for i in range(l-1):
    byte = 0
    val = p[i]
    for nf in range(8):
      tdi.value=(val >> nf) & 1
      tck.value=0
      tck.value=1
      if tdo.value:
        byte |= 1 << nf
    if w:
      w[i] = byte # write byte
  byte = 0
  val = p[l-1] # read last byte
  for nf in range(7): # first 7 bits
    tdi.value=(val >> nf) & 1
    tck.value=0
    tck.value=1
    if tdo.value:
      byte |= 1 << nf
  # last bit
  if last:
    tms.value=1
  tdi.value=(val >> 7) & 1
  tck.value=0
  tck.value=1
  if tdo.value:
    byte |= 1 << 7
  if w:
    w[l-1] = byte # write last byte

def send_int_msb1st(val:int, last:int, bits:int):
  #global tck,tms,tdi,tdo
  tms.value=0
  for nf in range(bits-1):
    tdi.value=(val >> (7-nf)) & 1
    tck.value=0
    tck.value=1
  if last:
    tms.value=1
  tdi.value=val & 1
  tck.value=0
  tck.value=1
  
# TAP to "reset" state
def reset_tap():
  #global tck,tms,tdi,tdo
  for n in range(6):
    send_tms(1) # -> Test Logic Reset

# TAP should be in "idle" state
# TAP returns to "select DR scan" state
def runtest_idle(count:int, duration_ms:int):
  #global tck,tms,tdi,tdo
  leave=int(monotonic_ns()) + duration_ms*1000000
  for n in range(count):
    send_tms(0) # -> idle
  while int(monotonic_ns()) < leave:
    send_tms(0) # -> idle
  send_tms(1) # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
def sir(data):
  send_tms(1) # -> select IR scan
  send_tms(0) # -> capture IR
  send_tms(0) # -> shift IR
  send_read_buf_lsb1st(data,1,None) # -> exit 1 IR
  send_tms0111() # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
# finish with n idle cycles during minimum of ms time
def sir_idle(data, n:int, ms:int):
  send_tms(1) # -> select IR scan
  send_tms(0) # -> capture IR
  send_tms(0) # -> shift IR
  send_read_buf_lsb1st(data,1,None) # -> exit 1 IR
  send_tms(0) # -> pause IR
  send_tms(1) # -> exit 2 IR
  send_tms(1) # -> update IR
  runtest_idle(n+1, ms) # -> select DR scan

def sdr(data):
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(data,1,None)
  send_tms0111() # -> select DR scan

def sdr_idle(data, n:int, ms:int):
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(data,1,None)
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  runtest_idle(n+1, ms) # -> select DR scan

# sdr buffer will be overwritten with response
def sdr_response(data):
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(data,1,memoryview(data))
  send_tms0111() # -> select DR scan

def check_response(response, expected, mask=0xFFFFFFFF, message=""):
  if (response & mask) != expected:
    print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

def idcode():
  bitbang_tms_on()
  bitbang_jtag_on()
  #led.value=1
  reset_tap()
  runtest_idle(1,0)
  #sir(b"\xE0")
  id_bytes = bytearray(4)
  sdr_response(id_bytes)
  #led.value=0
  bitbang_jtag_off()
  bitbang_tms_off()
  return unpack("<I", id_bytes)[0]

# common JTAG open for both program and flash
def common_open():
  bitbang_tms_on()
  bitbang_jtag_on()
  #led.value=1
  reset_tap()
  runtest_idle(1,0)
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

def stopwatch_start():
  global stopwatch_ns
  stopwatch_ns = monotonic_ns()

def stopwatch_stop(bytes_uploaded):
  elapsed_ms = (monotonic_ns() - stopwatch_ns)//1000000
  transfer_rate_MBps = 0
  if elapsed_ms > 0:
    transfer_rate_kBps = bytes_uploaded // elapsed_ms
  print("%d bytes uploaded in %d ms (%d kB/s)" % (bytes_uploaded, elapsed_ms, transfer_rate_kBps))

def open_file(filename, gz=False):
  filedata = open(filename, "rb")
  #if gz:
  #  import uzlib
  #  return uzlib.DecompIO(filedata,31)
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
  #if gz:
  #  import uzlib
  #  return uzlib.DecompIO(s,31)
  return s

def filedata_gz(filepath):
  gz = filepath.endswith(".gz")
  if filepath.startswith("http://") or filepath.startswith("/http:/"):
    filedata = open_web(filepath, gz)
  else:
    filedata = open_file(filepath, gz)
  return filedata, gz

spi_jtag_on()
spi_jtag_off()
bitbang_tms_on()
bitbang_jtag_on()
bitbang_jtag_input()
bitbang_jtag_off()
bitbang_tms_off()
