# circuitpython ESP32S2
# SPI LOOPBACK TEST

# connect MISO-MOSI IO35-IO37

from time import sleep,monotonic_ns
import board, busio, digitalio
from micropython import const
from struct import pack, unpack
from gc import collect

class spitest:

  def init_pinout_jtag(self):
    #self.gpio_tdi = board.IO11
    #self.gpio_tck = board.IO12
    #self.gpio_tdo = board.IO13
    #self.gpio_tms = board.IO14
    self.gpio_tdi = board.IO35
    self.gpio_tck = board.IO36
    self.gpio_tdo = board.IO37
    self.gpio_tms = board.IO38

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
  
  def loopback(self,n=3):
    print("loopback IO35-IO37")
    tx0=bytearray("1234")
    tx1=bytearray("ABCD")
    rx=bytearray(len(tx0))
    for i in range(n):
      self.bitbang_jtag_on()
      self.bitbang_jtag_off()
      self.spi_jtag_on()
      self.hwspi.write_readinto(tx0,rx)
      self.spi_jtag_off()
      print(rx, "ok" if rx==tx0 else "fail")
      sleep(0.5)
      self.bitbang_jtag_on()
      self.bitbang_jtag_off()
      self.spi_jtag_on()
      self.hwspi.write_readinto(tx1,rx)
      self.spi_jtag_off()
      print(rx, "ok" if rx==tx1 else "fail")
      sleep(0.5)

spitest().loopback()
