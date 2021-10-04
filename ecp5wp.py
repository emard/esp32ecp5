# micropython ESP32
# ECP5 JTAG FLASH protection tool

# AUTHOR=EMARD
# LICENSE=BSD

from time import ticks_ms, sleep_ms
from machine import SPI, Pin
from micropython import const
from struct import unpack
from uctypes import addressof
#from gc import collect

# FJC-ESP32-V0r2 pluggable
#gpio_tms = const(4)
#gpio_tck = const(16)
#gpio_tdi = const(15)
#gpio_tdo = const(2)
#gpio_tcknc = const(21)
#gpio_led = const(19)
# ULX3S v3.0.x
gpio_tms = const(21)
gpio_tck = const(18)
gpio_tdi = const(23)
gpio_tdo = const(19)
gpio_tcknc = const(17) # free pin for SPI workaround
gpio_led = const(5)
# ULX3S v3.1.x
#gpio_tms = const(5)   # BLUE LED - 549ohm - 3.3V
#gpio_tck = const(18)
#gpio_tdi = const(23)
#gpio_tdo = const(34)
#gpio_tcknc = const(21) # 1,2,3,19,21 free pin for SPI workaround
#gpio_led = const(19)

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

spi_freq = const(20000000) # Hz JTAG clk frequency
# -1 for JTAG over SOFT SPI slow, compatibility
#  1 or 2 for JTAG over HARD SPI fast
#  2 is preferred as it has default pinout wired
spi_channel = const(2) # -1 soft, 1:sd, 2:jtag
#flash_read_size = const(2048)
#flash_write_size = const(256)
#flash_erase_size = const(4096)
#flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8, 262144:0xD8 } # erase commands from FLASH PDF
#flash_era = bytearray([flash_erase_cmd[flash_erase_size],0,0])
#flash_req=bytearray(4)
read_status=bytearray([5])
status=bytearray(1)
rb=bytearray(256) # reverse bits
init_reverse_bits()

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
def send_tms(val:int):
  if val:
    tms.on()
  else:
    tms.off()
  tck.off()
  tck.on()

# exit 1 DR -> select DR scan
def send_tms0111():
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  send_tms(1) # -> select DR scan

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
  while int(ticks_ms())-leave < 0:
    send_tms(0) # -> idle
  send_tms(1) # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
@micropython.viper
def sir(buf):
  send_tms(1) # -> select IR scan
  send_tms(0) # -> capture IR
  send_tms(0) # -> shift IR
  send_read_buf_lsb1st(buf,1,0) # -> exit 1 IR
  send_tms0111() # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
# finish with n idle cycles during minimum of ms time
@micropython.viper
def sir_idle(buf, n:int, ms:int):
  send_tms(1) # -> select IR scan
  send_tms(0) # -> capture IR
  send_tms(0) # -> shift IR
  send_read_buf_lsb1st(buf,1,0) # -> exit 1 IR
  send_tms(0) # -> pause IR
  send_tms(1) # -> exit 2 IR
  send_tms(1) # -> update IR
  runtest_idle(n+1,ms) # -> select DR scan

@micropython.viper
def sdr(buf):
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms0111() # -> select DR scan

@micropython.viper
def sdr_idle(buf, n:int, ms:int):
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms(0) # -> pause DR
  send_tms(1) # -> exit 2 DR
  send_tms(1) # -> update DR
  runtest_idle(n+1, ms) # -> select DR scan

# sdr buffer will be overwritten with response
@micropython.viper
def sdr_response(buf):
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  send_read_buf_lsb1st(buf,1,addressof(buf))
  send_tms0111() # -> select DR scan

def check_response(response, expected, mask=0xFFFFFFFF, message=""):
  if (response & mask) != expected:
    print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

# common JTAG open for both program and flash
def common_open():
  spi_jtag_on()
  hwspi.init(sck=Pin(gpio_tcknc)) # avoid TCK-glitch
  bitbang_jtag_on()
  led.on()
  reset_tap()
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

# call this before sending the flash image
# FPGA will enter flashing mode
# TAP should be in "select DR scan" state
@micropython.viper
def flash_open():
  common_open()
  reset_tap()
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
  send_tms(0) # -> capture DR
  send_tms(0) # -> shift DR
  swspi.write(read_status) # READ STATUS REGISTER
  swspi.readinto(status)
  while retry > 0:
    swspi.readinto(status)
    if (int(status[0]) & mask) == 0:
      break
    sleep_ms(1)
    retry -= 1
  send_tms(1) # -> exit 1 DR # exit at byte incomplete
  #send_int_msb1st(0,1,8) # exit at byte complete
  send_tms0111() # -> select DR scan
  if retry <= 0:
    print("error %d flash status 0x%02X & 0x%02X != 0" % (n,status[0],mask))

# call this after uploading all of the flash blocks,
# this will exit FPGA flashing mode and start the bitstream
@micropython.viper
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
  reset_tap()
  led.off()
  bitbang_jtag_off()

# write protection tool for IS25LP128
# https://www.issi.com/WW/pdf/IS25LP128.pdf
# prot=0: unprotect
# prot=6: protect first 2MB
def is25lp128(prot=0x06):
  flash_open()
  # write function register
  # factory default is protecting the bottom (... - 0xFFFFFF)
  # now set to protect the top (0x000000 - ...).
  # NOTE: once set to protect the top, can't be reset back to protect the bottom!
  # see datasheet p.17 t.6.5, p.50 s.8.19
  sdr(bytearray([rb[0x06]])) # SPI WRITE ENABLE
  flash_wait_status(1011)
  sdr(bytearray([rb[0x42],rb[0x02]])) # function reg = 0x02 TBS=1 OTP warning: once set, can't be reset!
  flash_wait_status(2012)
  # write status register value prot=6 to protect 2MB (0x000000 - 0x1FFFFF)
  # see datasheet p.14 t.6.3
  sdr(bytearray([rb[0x06]])) # SPI WRITE ENABLE
  flash_wait_status(1021)
  sdr(bytearray([rb[0x01],rb[prot<<2]])) # status reg = prot<<2
  flash_wait_status(2022)
  flash_close()
