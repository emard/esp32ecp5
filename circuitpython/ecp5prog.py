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

class ecp5:

  def init_pinout_jtag(self):
    self.gpio_tdi = board.IO11
    self.gpio_tck = board.IO12
    self.gpio_tdo = board.IO13
    self.gpio_tms = board.IO14  # BLUE LED - 549ohm - 3.3V
    #self.gpio_tdi = board.IO35
    #self.gpio_tck = board.IO36
    #self.gpio_tdo = board.IO37
    #self.gpio_tms = board.IO38  # BLUE LED - 549ohm - 3.3V

  def bitbang_tms_on(self):
    self.tms=digitalio.DigitalInOut(self.gpio_tms)
    self.tms.direction=digitalio.Direction.OUTPUT

  def bitbang_tms_off(self):
    self.tms.deinit()

  def bitbang_jtag_on(self):
    self.tck=digitalio.DigitalInOut(self.gpio_tck)
    self.tck.direction=digitalio.Direction.OUTPUT
    self.tdi=digitalio.DigitalInOut(self.gpio_tdi)
    self.tdi.direction=digitalio.Direction.OUTPUT
    self.tdo=digitalio.DigitalInOut(self.gpio_tdo)
    self.tdo.direction=digitalio.Direction.INPUT

  def bitbang_jtag_off(self):
    self.tck.deinit()
    self.tdo.deinit()
    self.tdi.deinit()

  def bitbang_jtag_input(self):
    self.tck.direction=digitalio.Direction.INPUT
    self.tms.direction=digitalio.Direction.INPUT
    self.tdi.direction=digitalio.Direction.INPUT
    self.tdo.direction=digitalio.Direction.INPUT

  def spi_jtag_on(self):
    self.hwspi=busio.SPI(clock=self.gpio_tck,MOSI=self.gpio_tdi,MISO=self.gpio_tdo)
    while not self.hwspi.try_lock():
      pass
    self.hwspi.configure(baudrate=self.spi_freq,polarity=1,phase=1)

  def spi_jtag_off(self):
    self.hwspi.deinit()
    del self.hwspi

  def __init__(self):
    self.spi_freq = const(40000000) # Hz JTAG clk frequency
    self.init_pinout_jtag()
    self.spi_jtag_on()
    self.spi_jtag_off()
    self.bitbang_tms_on()
    self.bitbang_jtag_on()
    self.bitbang_jtag_input()
    self.bitbang_jtag_off()
    self.bitbang_tms_off()

  def send_tms(self, tms:int):
    self.tms.value=tms
    self.tck.value=0
    self.tck.value=1

  def send_read_data_buf(self, buf, last:int, w):
    p = memoryview(buf)
    l = int(len(buf))
    val = 0
    self.tms.value=0
    for i in range(l-1):
      byte = 0
      val = p[i]
      for nf in range(8):
        self.tdi.value=(val >> nf) & 1
        self.tck.value=0
        self.tck.value=1
        if self.tdo.value:
          byte |= 1 << nf
      if w:
        w[i] = byte # write byte
    byte = 0
    val = p[l-1] # read last byte
    for nf in range(7): # first 7 bits
      self.tdi.value=(val >> nf) & 1
      self.tck.value=0
      self.tck.value=1
      if self.tdo.value:
        byte |= 1 << nf
    # last bit
    if last:
      self.tms.value=1
    self.tdi.value=(val >> 7) & 1
    self.tck.value=0
    self.tck.value=1
    if self.tdo.value:
      byte |= 1 << 7
    if w:
      w[l-1] = byte # write last byte

  def send_data_byte_reverse(self, val:int, last:int, bits:int):
    self.tms.value=0
    for nf in range(bits-1):
      self.tdi.value=(val >> (7-nf)) & 1
      self.tck.value=0
      self.tck.value=1
    if last:
      self.tms.value=1
    self.tdi.value=val & 1
    self.tck.value=0
    self.tck.value=1
    
  # TAP to "reset" state
  def reset_tap(self):
    for n in range(6):
      self.send_tms(1) # -> Test Logic Reset

  # TAP should be in "idle" state
  # TAP returns to "select DR scan" state
  def runtest_idle(self, count:int, duration_ms:int):
    leave=int(monotonic_ns()) + duration_ms*1000000
    for n in range(count):
      self.send_tms(0) # -> idle
    while int(monotonic_ns()) < leave:
      self.send_tms(0) # -> idle
    self.send_tms(1) # -> select DR scan
  
  # send SIR command (bytes)
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state
  def sir(self, sir):
    self.send_tms(1) # -> select IR scan
    self.send_tms(0) # -> capture IR
    self.send_tms(0) # -> shift IR
    self.send_read_data_buf(sir, 1, None) # -> exit 1 IR
    self.send_tms(0) # -> pause IR
    self.send_tms(1) # -> exit 2 IR
    self.send_tms(1) # -> update IR
    self.send_tms(1) # -> select DR scan

  # send SIR command (bytes)
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state
  # finish with n idle cycles during minimum of ms time
  def sir_idle(self, sir, n:int, ms:int):
    self.send_tms(1) # -> select IR scan
    self.send_tms(0) # -> capture IR
    self.send_tms(0) # -> shift IR
    self.send_read_data_buf(sir, 1, None) # -> exit 1 IR
    self.send_tms(0) # -> pause IR
    self.send_tms(1) # -> exit 2 IR
    self.send_tms(1) # -> update IR
    self.runtest_idle(n+1, ms) # -> select DR scan

  def sdr(self, sdr):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.send_read_data_buf(sdr,1,None)
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.send_tms(1) # -> select DR scan

  def sdr_idle(self, sdr, n:int, ms:int):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.send_read_data_buf(sdr,1,None)
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.runtest_idle(n+1, ms) # -> select DR scan

  # sdr buffer will be overwritten with response
  def sdr_response(self, sdr):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.send_read_data_buf(sdr,1,memoryview(sdr))
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.send_tms(1) # -> select DR scan

  def check_response(self, response, expected, mask=0xFFFFFFFF, message=""):
    if (response & mask) != expected:
      print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

  def idcode(self):
    self.bitbang_tms_on()
    self.bitbang_jtag_on()
    #self.led.value=1
    self.reset_tap()
    self.runtest_idle(1,0)
    self.sir(b"\xE0")
    id_bytes = bytearray(4)
    self.sdr_response(id_bytes)
    #self.led.value=0
    self.bitbang_jtag_off()
    self.bitbang_tms_off()
    return unpack("<I", id_bytes)[0]

  # common JTAG open for both program and flash
  def common_open(self):
    self.bitbang_tms_on()
    self.bitbang_jtag_on()
    #self.led.value=1
    self.reset_tap()
    self.runtest_idle(1,0)
    #self.sir(b"\xE0") # read IDCODE
    #self.sdr(pack("<I",0), expected=pack("<I",0), message="IDCODE")
    self.sir(b"\x1C") # LSC_PRELOAD: program Bscan register
    self.sdr(bytearray([0xFF for i in range(64)]))
    self.sir(b"\xC6") # ISC ENABLE: Enable SRAM programming mode
    self.sdr_idle(b"\x00",2,10)
    self.sir_idle(b"\x3C",2,1) # LSC_READ_STATUS
    status = bytearray(4)
    self.sdr_response(status)
    self.check_response(unpack("<I",status)[0], mask=0x24040, expected=0, message="FAIL status")
    self.sir(b"\x0E") # ISC_ERASE: Erase the SRAM
    self.sdr_idle(b"\x01",2,10)
    self.sir_idle(b"\x3C",2,1) # LSC_READ_STATUS
    status = bytearray(4)
    self.sdr_response(status)
    self.check_response(unpack("<I",status)[0], mask=0xB000, expected=0, message="FAIL status")
  
  # call this before sending the bitstram
  # FPGA will enter programming mode
  # after this TAP will be in "shift DR" state
  def prog_open(self):
    self.common_open()
    self.sir(b"\x46") # LSC_INIT_ADDRESS
    self.sdr_idle(b"\x01",2,10)
    self.sir(b"\x7A") # LSC_BITSTREAM_BURST
    # ---------- bitstream begin -----------
    self.send_tms(0) # -> capture DR
    #self.send_tms(0) # -> shift DR NOTE will be send during TCK glitch
    self.bitbang_jtag_off() # NOTE TCK glitch
    self.spi_jtag_on()

  def prog_stream_done(self):
    # switch from hardware SPI to bitbanging done after prog_stream()
    self.spi_jtag_off()

  # call this after uploading all of the bitstream blocks,
  # this will exit FPGA programming mode and start the bitstream
  # returns status True-OK False-Fail
  def prog_close(self):
    self.bitbang_jtag_on()
    self.send_tms(1) # -> exit 1 DR
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    #self.send_tms(0) # -> idle, disabled here as runtest_idle does the same
    self.runtest_idle(100, 10)
    # ---------- bitstream end -----------
    self.sir_idle(b"\xC0",2,1) # read usercode
    usercode = bytearray(4)
    self.sdr_response(usercode)
    self.check_response(unpack("<I",usercode)[0],expected=0,message="FAIL usercode")
    self.sir_idle(b"\x26",2,200) # ISC DISABLE
    self.sir_idle(b"\xFF",2,1) # BYPASS
    self.sir(b"\x3C") # LSC_READ_STATUS
    status = bytearray(4)
    self.sdr_response(status)
    status = unpack("<I",status)[0]
    self.check_response(status,mask=0x2100,expected=0x100,message="FAIL status")
    done = True
    if (status & 0x2100) != 0x100:
      done = False
    self.reset_tap()
    #self.led.value=0
    self.bitbang_jtag_input()
    self.bitbang_jtag_off()
    self.bitbang_tms_off()
    return done

  def stopwatch_start(self):
    self.stopwatch_ns = monotonic_ns()
  
  def stopwatch_stop(self, bytes_uploaded):
    elapsed_ms = (monotonic_ns() - self.stopwatch_ns)//1000000
    transfer_rate_MBps = 0
    if elapsed_ms > 0:
      transfer_rate_kBps = bytes_uploaded // elapsed_ms
    print("%d bytes uploaded in %d ms (%d kB/s)" % (bytes_uploaded, elapsed_ms, transfer_rate_kBps))

  def prog_stream(self, filedata, blocksize=16384):
    self.prog_open()
    bytes_uploaded = 0
    self.stopwatch_start()
    block = bytearray(blocksize)
    while True:
      if filedata.readinto(block):
        self.hwspi.write(block)
        bytes_uploaded += len(block)
      else:
        break
    self.stopwatch_stop(bytes_uploaded)
    self.prog_stream_done()

  def open_file(self, filename, gz=False):
    filedata = open(filename, "rb")
    if gz:
      import uzlib
      return uzlib.DecompIO(filedata,31)
    return filedata

  def open_web(self, url, gz=False):
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

  def filedata_gz(self, filepath):
    gz = filepath.endswith(".gz")
    if filepath.startswith("http://") or filepath.startswith("/http:/"):
      filedata = self.open_web(filepath, gz)
    else:
      filedata = self.open_file(filepath, gz)
    return filedata, gz

# easier command typing
def idcode():
  return ecp5().idcode()

def prog(filepath, prog_close=True):
  board = ecp5()
  filedata, gz = board.filedata_gz(filepath)
  if filedata:
    if gz:
      board.prog_stream(filedata,blocksize=4096)
    else:
      board.prog_stream(filedata,blocksize=4096)
    # NOTE now the SD card can be released before bitstream starts
    if prog_close:
      return board.prog_close() # start the bitstream
    return True
  return False
