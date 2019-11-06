# micropython ESP32

# usage
# >>> import tapwalk                                                              
# >>> t=tapwalk.tapwalk()                                                         
# >>> t.idcode()                                                                    
# 43                                                                              
# 10                                                                              
# 11                                                                              
# 41                                                                              

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
    for nf in range(0, 8):
      self.send_bit((val >> nf) & 1, (last & int((nf == 7) == True)))
      byte |= self.tdo.value() << nf
    return byte

  def idcode(self):
    print("demo")
    self.led.on()
    for n in range(0,6):
      self.send_bit(0,1) # Test Logic Reset 1
    self.send_bit(0,0) # -> idle
    # State = IDLE
    self.send_bit(0,1) # -> select DR scan

    self.send_bit(0,1) # -> select IR scan
    self.send_bit(0,0) # -> capture IR
    self.send_bit(0,0) # -> shift IR
    # IDCODE Instruction
    self.read_data_byte(0xE0,1) # -> exit IR
    self.send_bit(0,1) # -> update IR
    self.send_bit(0,1) # -> select DR scan

    self.send_bit(0,0) # -> capture DR
    self.send_bit(0,0) # -> shift DR
    # read data response from IDCODE
    print("%02X" % self.read_data_byte(0,0))
    print("%02X" % self.read_data_byte(0,0))
    print("%02X" % self.read_data_byte(0,0))
    print("%02X" % self.read_data_byte(0,1))
    self.send_bit(0,1) # -> update DR
    self.send_bit(0,1) # -> select DR scan

    self.led.off()
