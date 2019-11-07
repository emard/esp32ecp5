# micropython ESP32

# usage
# >>> import tapwalk                                                              
# >>> t=tapwalk.tapwalk()                                                         
# >>> t.idcode()                                                                    
# 43                                                                              
# 10                                                                              
# 11                                                                              
# 41                                                                              

import time
from machine import SPI, Pin

class tapwalk:

  # debugging with OLED to see bus state
  def pinout_oled(self):
    self.led=Pin( 5,Pin.OUT)
    self.tms=Pin(15,Pin.OUT)
    self.tck=Pin(14,Pin.OUT)
    self.tdi=Pin(13,Pin.OUT)
    self.tdo=Pin(12,Pin.IN)

  # actual JTAG
  def pinout_jtag(self):
    self.led=Pin( 5,Pin.OUT)
    self.tms=Pin(21,Pin.OUT)
    self.tck=Pin(18,Pin.OUT)
    self.tdi=Pin(23,Pin.OUT)
    self.tdo=Pin(19,Pin.IN)

  # software SPI

#  def swspi_oled(self):
#    # software SPI -1 currently can't have firstbit=SPI.LSB
#    self.spi=SPI(-1, baudrate=10000000, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(14), mosi=Pin(13), miso=Pin(12))

  # hardware SPI (oled debug)

#  def hwspi_oled(self):
#    self.spi=SPI(1, baudrate=10000000, polarity=1, phase=1, bits=8, firstbit=SPI.LSB, sck=Pin(14), mosi=Pin(13), miso=Pin(12))

#  # HW spi problem: glitch
#  def spi_tdi(self):
#    self.spi.init(mosi=Pin(13))
  
#  # HW spi problem: glitch
#  def spi_tms(self):
#    self.spi.init(mosi=Pin(15))

  # hardware SPI (real jtag)

#  def hwspi_jtag(self):
#    self.spi=SPI(2, baudrate=10000000, polarity=1, phase=1, bits=8, firstbit=SPI.LSB, sck=Pin(18), mosi=Pin(23), miso=Pin(19))

#  # HW spi problem: glitch
#  def hwspi_tdi(self):
#    self.spi.init(mosi=Pin(23))
  
#  # HW spi problem: glitch
#  def hwspi_tms(self):
#    self.spi.init(mosi=Pin(21))

  def __init__(self):
#    self.pinout_oled()
    self.pinout_jtag()

  def __call__(self):
    print("call")

  def bitreverse(self,x):
    y = 0
    for i in range(8):
        if (x >> (7 - i)) & 1 == 1:
            y |= (1 << i)
    return y

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

    
  def read_data_byte(self, val, last):
    byte = 0
    for nf in range(8):
      self.send_bit((val >> nf) & 1, (last & int((nf == 7) == True)))
      byte |= self.tdo.value() << nf
    return byte
    
  # TAP to "reset" state
  # and TAP returned to "select DR scan" state
  def reset_tap(self):
    for n in range(6):
      self.send_bit(0,1) # -> Test Logic Reset
    self.send_bit(0,0) # -> idle
    self.send_bit(0,1) # -> select DR scan

  # TAP should be in "idle" state
  # TAP returns to "select DR scan" state
  def runtest_idle(self, count, duration):
    leave=time.ticks_ms() + int(duration*1000)
    for n in range(count):
      self.send_bit(0,0) # -> idle
    while time.ticks_ms() < leave:
      self.send_bit(0,0) # -> idle
    self.send_bit(0,1) # -> select DR scan
  
  # send SIR command (byte integer)
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state by default
  # TAP returns to "idle" state if specified 
  def sir(self, sir, idle=False):
    self.send_bit(0,1) # -> select IR scan
    self.send_bit(0,0) # -> capture IR
    self.send_bit(0,0) # -> shift IR
    self.read_data_byte(sir,1) # -> exit 1 IR
    self.send_bit(0,0) # -> pause IR
    self.send_bit(0,1) # -> exit 2 IR
    self.send_bit(0,1) # -> update IR
    if idle:
      self.send_bit(0,0) # -> idle
    else:
      self.send_bit(0,1) # -> select DR scan

  # send SDR data (byte string)
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state by default
  # TAP returns to "idle" state if specified 
  def sdr(self, sdr, idle=False):
    self.send_bit(0,0) # -> capture DR
    self.send_bit(0,0) # -> shift DR
    for byte in sdr[:-1]:
      self.read_data_byte(byte,0) # not last
    self.read_data_byte(sdr[-1],1) # last, exit 1 DR
    self.send_bit(0,0) # -> pause DR
    self.send_bit(0,1) # -> exit 2 DR
    self.send_bit(0,1) # -> update DR
    if idle:
      self.send_bit(0,0) # -> idle
    else:
      self.send_bit(0,1) # -> select DR scan
  
  # send SDR data (byte string) and print result
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state by default
  # TAP returns to "idle" state if specified 
  def sdr_print(self, sdr, idle=False):
    self.send_bit(0,0) # -> capture DR
    self.send_bit(0,0) # -> shift DR
    for byte in sdr[:-1]:
      print("%02X" % self.read_data_byte(byte,0),end="") # not last
    print("%02X" % self.read_data_byte(sdr[-1],1)) # last, exit 1 DR
    self.send_bit(0,0) # -> pause DR
    self.send_bit(0,1) # -> exit 2 DR
    self.send_bit(0,1) # -> update DR
    if idle:
      self.send_bit(0,0) # -> idle
    else:
      self.send_bit(0,1) # -> select DR scan

  def idcode(self):
    print("idcode")
    self.led.on()
    self.reset_tap()
    self.sir(0xE0)
    self.sdr_print(b"\x00\x00\x00\x00")
    self.led.off()
  
  def program(self, filename):
    print("program")
    self.led.on()
    self.reset_tap()
    self.sir(0xE0)
    self.sdr_print(b"\x00\x00\x00\x00")
    self.sir(0x1C)
    self.sdr_print([0xFF for i in range(64)])
    self.sir(0xC6)
    self.sdr(b"\x00", idle=True)
    self.runtest_idle(2,1.0E-2)
    self.sir(0x0E)
    self.sdr(b"\x01", idle=True)
    self.runtest_idle(2,1.0E-2)
    self.sir(0x3C)
    self.sdr_print(b"\x00\x00\x00\x00")
    print("00000000 mask 00B00000");
    self.sir(0x46)
    self.sdr(b"\x01", idle=True)
    self.runtest_idle(2,1.0E-2)
    self.sir(0x7A, idle=True)
    self.runtest_idle(2,1.0E-2)
    # bitstream begin
    with open(filename, "rb") as filedata:
      while True:
        block = filedata.read(1024)
        block = bytes([self.bitreverse(x) for x in block])
        if block:
          print(".",end="")
          self.sdr(block)
        else:
          print("*")
          break
    # bitstream end
    self.sir(0xFF, idle=True)
    self.runtest_idle(100,1.0E-2)
    self.sir(0xC0, idle=True)
    self.runtest_idle(2,1.0E-2)
    self.sdr_print(b"\x00\x00\x00\x00")
    print("00000000 mask FFFFFFFF");
    self.sir(0x26, idle=True)
    self.runtest_idle(2,2.0E-1)
    self.sir(0xFF, idle=True)
    self.runtest_idle(2,1.0E-3)
    self.sir(0x3C)
    self.sdr_print(b"\x00\x00\x00\x00")
    print("00010000 mask 00210000");

    self.led.off()
