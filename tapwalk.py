# micropython ESP32

import time
from machine import SPI, Pin

class tapwalk:

  def init_pinout_jtag(self):
    self.gpio_tms = 21
    self.gpio_tck = 18
    self.gpio_tdi = 23
    self.gpio_tdo = 19

#  def init_pinout_oled(self):
#    self.gpio_tms = 15
#    self.gpio_tck = 14
#    self.gpio_tdi = 13
#    self.gpio_tdo = 12


  def bitbang_jtag_on(self):
    self.led=Pin(self.gpio_led,Pin.OUT)
    self.tms=Pin(self.gpio_tms,Pin.OUT)
    self.tck=Pin(self.gpio_tck,Pin.OUT)
    self.tdi=Pin(self.gpio_tdi,Pin.OUT)
    self.tdo=Pin(self.gpio_tdo,Pin.IN)

  def bitbang_jtag_off(self):
    self.led=Pin(self.gpio_led,Pin.IN)
    self.tms=Pin(self.gpio_tms,Pin.IN)
    self.tck=Pin(self.gpio_tck,Pin.IN)
    self.tdi=Pin(self.gpio_tdi,Pin.IN)
    self.tdo=Pin(self.gpio_tdo,Pin.IN)
    a = self.led.value()
    a = self.tms.value()
    a = self.tck.value()
    a = self.tdo.value()
    a = self.tdi.value()
    del self.led
    del self.tms
    del self.tck
    del self.tdi
    del self.tdo

  # accelerated SPI 
  def spi_jtag_on(self):
    self.spi=SPI(self.spi_channel, baudrate=self.spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(self.gpio_tck), mosi=Pin(self.gpio_tdi), miso=Pin(self.gpio_tdo))

  def spi_jtag_off(self):
    del self.spi

  def __init__(self):
    self.gpio_led = 5
    self.spi_channel = 2 # -1 soft, 1:oled, 2:jtag
    self.spi_freq = 30000000 # Hz
    self.init_pinout_jtag()
    #self.init_pinout_oled()

  def __call__(self):
    some_variable = 0

  def bitreverse(self,x):
    y = 0
    for i in range(8):
        if (x >> (7 - i)) & 1 == 1:
            y |= (1 << i)
    return y

  def send_tms(self, tms):
    if tms:
      self.tms.on()
    else:
      self.tms.off()
    self.tck.off()
    self.tck.on()

  def send_bit(self, tdi, tms):
    if tdi:
      self.tdi.on()
    else:
      self.tdi.off()
    if tms:
      self.tms.on()
    else:
      self.tms.off()
    self.tck.off()
    self.tck.on()

  def send_read_data_byte(self, val, last):
    byte = 0
    for nf in range(8):
      self.send_bit((val >> nf) & 1, (last & int((nf == 7) == True)))
      byte |= self.tdo.value() << nf
    return byte

  def send_read_data_byte_reverse(self, val, last):
    byte = 0
    for nf in range(8):
      self.send_bit((val >> (7-nf)) & 1, (last & int((nf == 7) == True)))
      byte |= self.tdo.value() << nf
    return byte
    
  # TAP to "reset" state
  def reset_tap(self):
    for n in range(6):
      self.send_tms(1) # -> Test Logic Reset

  # TAP should be in "idle" state
  # TAP returns to "select DR scan" state
  def runtest_idle(self, count, duration):
    leave=time.ticks_ms() + int(duration*1000)
    for n in range(count):
      self.send_tms(0) # -> idle
    while time.ticks_ms() < leave:
      self.send_tms(0) # -> idle
    self.send_tms(1) # -> select DR scan
  
  # send SIR command (bytes)
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state
  def sir(self, sir, idle=False):
    self.send_tms(1) # -> select IR scan
    self.send_tms(0) # -> capture IR
    self.send_tms(0) # -> shift IR
    for byte in sir[:-1]:
      self.send_read_data_byte(byte,0) # not last
    self.send_read_data_byte(sir[-1],1) # last, exit 1 DR
    self.send_tms(0) # -> pause IR
    self.send_tms(1) # -> exit 2 IR
    self.send_tms(1) # -> update IR
    if idle:
      #self.send_tms(0) # -> idle, disabled here as runtest_idle does it
      self.runtest_idle(idle[0]+1, idle[1])
    else:
      self.send_tms(1) # -> select DR scan

  # send SDR data (bytes) and print result
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state
  def sdr(self, sdr, verbose=False, idle=False):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    if verbose:
      for byte in sdr[:-1]:
        print("%02X" % byte,end="")
      print("%02X send" % sdr[-1])
      response = b""
      for byte in sdr[:-1]:
        response += bytes([self.send_read_data_byte(byte,0)]) # not last
      response += bytes([self.send_read_data_byte(sdr[-1],1)]) # last, exit 1 DR
      # print byte reverse - notation same as in SVF file
      for n in range(len(response)):
        print("%02X" % response[len(response)-n-1], end="")
      print(" response")
    else: # no print, faster
      for byte in sdr[:-1]:
        self.send_read_data_byte(byte,0) # not last
      self.send_read_data_byte(sdr[-1],1) # last, exit 1 DR
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    if idle:
      #self.send_tms(0) # -> idle, disabled here as runtest_idle does it
      self.runtest_idle(idle[0]+1, idle[1])
    else:
      self.send_tms(1) # -> select DR scan

  def idcode(self):
    print("idcode")
    self.bitbang_jtag_on()
    self.led.on()
    self.reset_tap()
    self.runtest_idle(1,0)
    self.sir(b"\xE0")
    self.sdr(b"\x00\x00\x00\x00", verbose=True)
    self.led.off()
    self.bitbang_jtag_off()
  
  def program(self, filename):
    print("program \"%s\"" % filename)
    with open(filename, "rb") as filedata:
      self.spi_jtag_on()
      self.spi.init(baudrate=self.spi_freq//2) # workarounds ESP32 micropython SPI bugs
      self.bitbang_jtag_on()
      self.led.on()
      self.reset_tap()
      self.runtest_idle(1,0)
      self.sir(b"\xE0") # read IDCODE
      self.sdr(b"\x00\x00\x00\x00", verbose=True)
      self.sir(b"\x1C")
      self.sdr([0xFF for i in range(64)])
      self.sir(b"\xC6")
      self.sdr(b"\x00", idle=(2,1.0E-2))
      self.sir(b"\x3C", idle=(2,1.0E-3)) # LSC_READ_STATUS
      self.sdr(b"\x00\x00\x00\x00", verbose=False)
      #print("00024040 &= 00000000 ? status");
      self.sir(b"\x0E") # ISC erase RAM
      self.sdr(b"\x01", idle=(2,1.0E-2))
      self.sir(b"\x3C", idle=(2,1.0E-3)) # LSC_READ_STATUS
      self.sdr(b"\x00\x00\x00\x00", verbose=False)
      #print("0000B000 &= 00000000 ? status");
      self.sir(b"\x46") # LSC_INIT_ADDRESS
      self.sdr(b"\x01", idle=(2,1.0E-2))
      self.sir(b"\x7A") # LSC_BITSTREAM_BURST
      # ---------- bitstream begin -----------
      # manually walk the TAP
      # we will be sending one long DR command
      self.send_tms(0) # -> capture DR
      self.send_tms(0) # -> shift DR
      bytes_uploaded = 0
      blocksize = 16384
      # switch from bitbanging to SPI mode must be glitchless at TCK line
      self.spi.init(baudrate=self.spi_freq)
      while True:
        block = filedata.read(blocksize)
        if block:
          #for byte in block:
          #  self.send_read_data_byte_reverse(byte,0)
          self.spi.write(block) # same as above but faster
          print(".",end="")
          bytes_uploaded += len(block)
        else:
          print("*")
          print("%d bytes uploaded" % bytes_uploaded)
          break
      spi_trick = False
      if spi_trick:
        # problem with HW SPI 1 and 2: change of MOSI line makes a TCK glitch
        # SW SPI -1: changes MOSI without a glich
        self.spi.init(mosi=Pin(self.gpio_tms))
        self.spi.write(b"\xB0") # 0xB = exit 1 DR, pause DR, exit 2 DR, update DR, 0x0 = 4xidle
        # switch from SPI to bitbanging must be glitchless at TCK line
        self.bitbang_jtag_on()
      else:
        # switch from SPI to bitbanging must be glitchless at TCK line
        self.bitbang_jtag_on()
        self.send_read_data_byte(0xFF,1) # last dummy byte 0xFF, exit 1 DR
        self.send_tms(0) # -> pause DR
        self.send_tms(1) # -> exit 2 DR
        self.send_tms(1) # -> update DR
      self.runtest_idle(100, 1.0E-2)
      # ---------- bitstream end -----------
      self.sir(b"\xC0", idle=(2,1.0E-3)) # read usercode
      self.sdr(b"\x00\x00\x00\x00", verbose=False)
      #print("FFFFFFFF &= 00000000 ? usercode");
      self.sir(b"\x26", idle=(2,2.0E-1)) # ISC DISABLE
      self.sir(b"\xFF", idle=(2,1.0E-3)) # BYPASS
      self.sir(b"\x3C") # LSC_READ_STATUS
      self.sdr(b"\x00\x00\x00\x00", verbose=True)
      print("00002100 &= 00000100 ? status");
      self.spi_jtag_off()
      self.reset_tap()
      self.led.off()
      self.bitbang_jtag_off()

print("usage:")
print("tap=tapwalk.tapwalk()")
print("tap.program(\"blink.bit\")")
print("tap.idcode()")
tap = tapwalk()
#tap.idcode()
tap.program("blink.bit")
