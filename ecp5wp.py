# micropython ESP32
# ECP5 JTAG FLASH protection tool

# AUTHOR=EMARD
# LICENSE=BSD

from time import ticks_ms, sleep_ms
from machine import SPI, SoftSPI, Pin
from micropython import const
from struct import unpack
from uctypes import addressof
import jtagpin
#from gc import collect

#@micropython.viper
#def init_reverse_bits():
#  #p8rb=ptr8(addressof(rb))
#  p8rb=memoryview(rb)
#  for i in range(256):
#    v=i
#    r=0
#    for j in range(8):
#      r<<=1
#      r|=v&1
#      v>>=1
#    p8rb[i]=r

spi_freq = const(20000000) # Hz JTAG clk frequency
#flash_read_size = const(2048)
#flash_write_size = const(256)
#flash_erase_size = const(4096)
#flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8, 262144:0xD8 } # erase commands from FLASH PDF
#flash_era = bytearray([flash_erase_cmd[flash_erase_size],0,0])
#flash_req=bytearray(4)
read_status=bytearray([5])
status=bytearray(1)
#rb=bytearray(256) # reverse bits
#init_reverse_bits()
discard=const(0) # discard running bitstream

def bitbang_jtag_on():
  global tck,tms,tdi,tdo,led
  led=Pin(jtagpin.led,Pin.OUT)
  tms=Pin(jtagpin.tms,Pin.OUT)
  tck=Pin(jtagpin.tck,Pin.OUT)
  tdi=Pin(jtagpin.tdi,Pin.OUT)
  tdo=Pin(jtagpin.tdo,Pin.IN)

def bitbang_jtag_off():
  global tck,tms,tdi,tdo,led
  led=Pin(jtagpin.led,Pin.IN)
  tms=Pin(jtagpin.tms,Pin.IN)
  tck=Pin(jtagpin.tck,Pin.IN)
  tdi=Pin(jtagpin.tdi,Pin.IN)
  tdo=Pin(jtagpin.tdo,Pin.IN)
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
  hwspi=SPI(2, baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(jtagpin.tck), mosi=Pin(jtagpin.tdi), miso=Pin(jtagpin.tdo))
  swspi=SoftSPI(baudrate=spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(jtagpin.tck), mosi=Pin(jtagpin.tdi), miso=Pin(jtagpin.tdo))

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

# exit 1 DR -> select DR scan
def send_tms0111():
  send_tms(0,1) # -> pause DR
  send_tms(1,3) # -> exit 2 DR -> update DR -> select DR scan

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

# TAP should be in "idle" state
# TAP returns to "select DR scan" state
@micropython.viper
def runtest_idle(count:int, duration_ms:int):
  leave=int(ticks_ms()) + duration_ms
  send_tms(0,count) # -> idle
  while int(ticks_ms())-leave < 0:
    send_tms(0,1) # -> idle
  send_tms(1,1) # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
@micropython.viper
def sir(buf):
  send_tms(1,1) # -> select IR scan
  send_tms(0,2) # -> capture IR -> shift IR
  send_read_buf_lsb1st(buf,1,0) # -> exit 1 IR
  send_tms0111() # -> select DR scan

# send SIR command (bytes)
# TAP should be in "select DR scan" state
# TAP returns to "select DR scan" state
# finish with n idle cycles during minimum of ms time
@micropython.viper
def sir_idle(buf, n:int, ms:int):
  send_tms(1,1) # -> select IR scan
  send_tms(0,2) # -> capture IR -> shift IR
  send_read_buf_lsb1st(buf,1,0) # -> exit 1 IR
  send_tms(0,1) # -> pause IR
  send_tms(1,2) # -> exit 2 IR -> update IR
  runtest_idle(n+1,ms) # -> select DR scan

@micropython.viper
def sdr(buf):
  send_tms(0,2) # -> capture DR -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms0111() # -> select DR scan

@micropython.viper
def sdr_idle(buf, n:int, ms:int):
  send_tms(0,2) # -> capture DR -> shift DR
  send_read_buf_lsb1st(buf,1,0)
  send_tms(0,1) # -> pause DR
  send_tms(1,2) # -> exit 2 DR -> update DR
  runtest_idle(n+1, ms) # -> select DR scan

# sdr buffer will be overwritten with response
@micropython.viper
def sdr_response(buf):
  send_tms(0,2) # -> capture DR -> shift DR
  send_read_buf_lsb1st(buf,1,addressof(buf))
  send_tms0111() # -> select DR scan

def check_response(response, expected, mask=0xFFFFFFFF, message=""):
  if (response & mask) != expected:
    print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

def idcode():
  bitbang_jtag_on()
  led.on()
  send_tms(1,6) # -> Test Logic Reset
  runtest_idle(1,0)
  #sir(b"\xE0")
  id_bytes = bytearray(4)
  sdr_response(id_bytes)
  led.off()
  bitbang_jtag_off()
  return unpack("<I", id_bytes)[0]


# common JTAG open for both program and flash
def common_open():
  spi_jtag_on()
  hwspi.init(sck=Pin(jtagpin.tcknc)) # avoid TCK-glitch
  bitbang_jtag_on()
  led.on()
  send_tms(1,6) # -> Test Logic Reset
  runtest_idle(1,0)
  #sir(b"\xE0") # read IDCODE
  #sdr(pack("<I",0), expected=pack("<I",0), message="IDCODE")
  if discard:
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
  send_tms(1,6) # -> Test Logic Reset
  runtest_idle(1,0)
  sir_idle(b"\xFF",32,0) # BYPASS
  sir(b"\x3A") # LSC_PROG_SPI
  sdr_idle(b"\xFE\x68",32,0)
  # ---------- flashing begin -----------
  # sdr(b"\x60") and other SPI FLASH commands
  # here are bitreverse() values of FLASH commands
  # found in datasheet. e.g.
  # \x1B -> 0xD8
  # \x60 -> 0x06 ...

@micropython.viper
def flash_wait_status(n:int):
  retry=n
  mask=1 # WIP bit (work-in-progress)
  send_tms(0,2) # -> capture DR -> shift DR
  swspi.write(read_status) # READ STATUS REGISTER
  swspi.readinto(status)
  while retry > 0:
    swspi.readinto(status)
    if (int(status[0]) & mask) == 0:
      break
    sleep_ms(1)
    retry -= 1
  send_tms(1,1) # -> exit 1 DR # exit at byte incomplete
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
  if discard:
    sir_idle(b"\x26",2,200) # ISC DISABLE
    sir_idle(b"\xFF",2,1) # BYPASS
    sir(b"\x79") # LSC_REFRESH reload the bitstream from flash
    sdr_idle(b"\x00\x00\x00",2,100)
  spi_jtag_off()
  send_tms(1,6) # -> Test Logic Reset
  led.off()
  bitbang_jtag_off()

def flash_send(seq):
  send_tms(0,2) # -> capture DR -> shift DR
  if len(seq)>1:
    swspi.write(seq[:-1]) # all except last byte
  send_int_msb1st(seq[-1],1,8) # last byte -> exit 1 DR
  send_tms0111() # -> select DR scan

def flash_sendrecv(send,recv):
  send_tms(0,2) # -> capture DR -> shift DR
  swspi.write(send)
  swspi.readinto(recv)
  #send_tms(1) # -> exit 1 DR # exit at byte incomplete
  send_int_msb1st(0,1,8) # complete dummy byte and exit
  send_tms0111() # -> select DR scan

def int2bin(a):
  bin=bytearray(8)
  for i in range(8):
    bin[7-i]=48+(a&1)
    a>>=1
  return bin

# write protection tool for IS25LP128
# https://www.issi.com/WW/pdf/IS25LP128.pdf
# prot=0: unprotect
# prot=6: protect first 2MB
def is25lp128_protect(prot=6):
  flash_open()
  # write function register
  # factory default is protecting the top (... - 0xFFFFFF)
  # now set to protect the bottom (0x000000 - ...).
  # NOTE: once set to protect the bottom, can't be reset back to protect the top
  # see datasheet p.17 t.6.5, p.50 s.8.19
  flash_send(b"\x06") # permanent write
  flash_wait_status(1011)
  flash_send(b"\x42\x02") # function reg = 0x02 TBS=1 OTP warning: once set, can't be reset!
  flash_wait_status(2012)
  # write status register value prot=6 to protect 2MB (0x000000 - 0x1FFFFF)
  # see datasheet p.14 t.6.3
  flash_send(b"\x06") # permanent write
  flash_wait_status(1021)
  flash_send(bytearray([1,prot<<2])) # status reg1=0x18 protect lower 2MB
  flash_wait_status(2022)
  flash_close()

def is25lp128_status():
  flash_open()
  status_reg1=bytearray(1)
  status_reg2=bytearray(1)
  flash_sendrecv(b"\x05",status_reg1)
  flash_sendrecv(b"\x48",status_reg2)
  flash_close()
  if discard:
    sleep_ms(1000)
  noyes_txt=("No","Yes")
  TBS=(status_reg2[0]>>1) & 1
  TBS_txt=("Top","Bottom")
  IRL=(status_reg2[0]>>4) & 15
  BP=(status_reg1[0]>>2) & 15
  QE=(status_reg1[0]>>6) & 1
  range_bytes = 32768<<BP
  if BP:
    if TBS:
      range="0x000000 - 0x%06X" % (range_bytes-1)
    else: # TBS=0
      range="0x%06X - 0xFFFFFF" % (0x1000000-range_bytes)
  else: # BP=0
    range="None"
  print("Read 0x05: Status Register = 0x%02X" % status_reg1[0])
  print(int2bin(status_reg1[0]).decode())
  print(".x...... QE  Quad Enable        : %s" % noyes_txt[QE])
  print("..xxxx.. BP  Protected Range    : %s" % range)
  print("Read 0x48: Function Register = 0x%02X" % status_reg2[0])
  print("%s OTP warning value 1 can't reset to 0" % int2bin(status_reg2[0]).decode())
  print("xxxx.... IRL Information Lock   : %d" % IRL)
  print("......x. TBS Top/Bottom Select  : %s" % TBS_txt[TBS])

# write protection tool for W25Q128JV, see datasheet p.18, p.26
# https://www.winbond.com/resource-files/w25q128jv%20revf%2003272018%20plus.pdf
# prot= 0: unprotect  
# prot=12: protecting first 2MB
def w25q128jv_protect(prot=12):
  flash_open()
  flash_wait_status(1021)
  flash_send(b"\x06") # permanent write
  flash_wait_status(1021)
  flash_send(bytearray([1,prot<<2])) # status reg1=0x30 protect lower 2MB
  flash_wait_status(1021)
  flash_send(b"\x06") # permanent write
  flash_wait_status(1021)
  flash_send(b"\x11\x60") # status reg3=0x60 WPS=0
  flash_wait_status(1021)
  #flash_send(b"\x50") # temporary write
  #flash_wait_status(1021)
  #flash_send(b"\x31\x01") # status reg2=0x01 lock status
  #flash_wait_status(1021)
  #status_reg1=bytearray(1)
  #flash_sendrecv(b"\x05",status_reg1)
  flash_close()
  #return status_reg1[0]

def w25q128jv_status():
  flash_open()
  status_reg1=bytearray(1)
  status_reg2=bytearray(1)
  status_reg3=bytearray(1)
  flash_sendrecv(b"\x05",status_reg1)
  flash_sendrecv(b"\x35",status_reg2)
  flash_sendrecv(b"\x15",status_reg3)
  flash_close()
  if discard:
    sleep_ms(1000)
  noyes_txt=("No","Yes")
  print("Read 0x05: Status Register-1 = 0x%02X" % status_reg1[0])
  SRP=(status_reg1[0]>>7) & 1
  SEC=(status_reg1[0]>>6) & 1
  SEC_txt=("64KB Blocks","4KB Sectors")
  TB=(status_reg1[0]>>5) & 1
  TB_txt=("Top","Bottom")
  BP=(status_reg1[0]>>2) & 7
  CMP=(status_reg2[0]>>6) & 1
  SEC_size=(128*1024,2048)
  range_bytes = SEC_size[SEC]<<BP
  if BP:
    if TB:
      if CMP:
        range="0x%06X - 0xFFFFFF" % (range_bytes)
      else: # CMP=0
        range="0x000000 - 0x%06X" % (range_bytes-1)
    else: # TB=0
      if CMP:
        range="0x000000 - 0x%06X" % (0xFFFFFF-range_bytes)
      else: # CMP=0
        range="0x%06X - 0xFFFFFF" % (0x1000000-range_bytes)
  else: # BP=0
    range="None"
  print(int2bin(status_reg1[0]).decode())
  print("x....... SRP Status Reg Protect by WP pin: %s" % noyes_txt[SRP])
  print(".x...... SEC Sector/Block Protect        : %s" % SEC_txt[SEC])
  print("..x..... TB  Top/Bottom Protect          : %s" % TB_txt[TB])
  print("...xxx.. BP  Protected Range             : %s" % range)
  print("Read 0x35: Status Register-2 = 0x%02X" % status_reg2[0])
  #CMP=(status_reg2[0]>>6) & 1
  LB=(status_reg2[0]>>3) & 7
  QE=(status_reg2[0]>>1) & 1
  SRL=status_reg2[0] & 1
  print("%s OTP warning value 1 can't reset to 0" % int2bin(status_reg2[0]).decode())
  print(".x...... CMP Complement Protect          : %s" % noyes_txt[CMP])
  print("..xxx... LB  Security Register Lock Bits : %d" % LB)
  print("......x. QE  Quad Enable                 : %s" % noyes_txt[QE])
  print(".......x SRL STATUS REGISTER LOCK        : %s" % noyes_txt[SRL])
  print("Read 0x15: Status Register-3 = 0x%02X" % status_reg3[0])
  print(int2bin(status_reg3[0]).decode())
  WPS=(status_reg3[0]>>2) & 1
  WPS_txt=("Defined by Register-1 and 2","Individual Sectors")
  DRV=(status_reg3[0]>>5) & 3
  DRV_strength=bytearray([100,75,50,25]) # %
  print(".xx..... DRV Output Driver Strength      : %d%%" % DRV_strength[DRV])
  print(".....x.. WPS Write Protection Scheme     : %s" % WPS_txt[WPS])

def detect():
  id=idcode()
  print("FPGA JTAG IDCODE 0x%08X" % id)
  if id==0:
    print("check pinout for v3.0.x/v3.1.x")
    return
  flash_open()
  manuf_dev_id=bytearray(2)
  flash_sendrecv(b"\x90\x00\x00\x00",manuf_dev_id)
  jedec_id=bytearray(3)
  flash_sendrecv(b"\x9F",jedec_id)
  unique_id=bytearray(8)
  flash_sendrecv(b"\x4B\x00\x00\x00\x00",unique_id)
  flash_close()
  if discard:
    sleep_ms(1000)
  print("Read 0x90: Manufacture/Device ID: %02X %02X" %
    (manuf_dev_id[0],manuf_dev_id[1]))
  print("Read 0x9F: JEDEC              ID: %02X %02X %02X" %
    (jedec_id[0],jedec_id[1],jedec_id[2]))
  print("Read 0x4B: Unique             ID: %02X %02X %02X %02X %02X %02X %02X %02X" %
    (unique_id[0],unique_id[1],unique_id[2],unique_id[3],unique_id[4],unique_id[5],unique_id[6],unique_id[7]))
  if manuf_dev_id==b"\x00\x00" or manuf_dev_id==b"\xFF\xFF":
    print("JTAG can't access SPI FLASH. Try")
    print("ESP32 passthru that drives WPn=1 HOLDn=1,")
    print("with SYSCONFIG MASTER_SPI_PORT=ENABLE in .lpf, without USRMCLK in .v")
    print("fujprog passthru.bit or edit this source: discard=1")
  if jedec_id==b"\xEF\x40\x18":
    print("Winbond W25Q128JV")
    if discard:
      sleep_ms(1000)
    w25q128jv_status()
    print("ecp5wp.w25q128jv_protect()")
    print("ecp5wp.w25q128jv_protect(0)")
  if jedec_id==b"\x9D\x60\x18":
    print("ISSI IS25LP128")
    if discard:
      sleep_ms(1000)
    is25lp128_status()
    print("ecp5wp.is25lp128_protect()")
    print("ecp5wp.is25lp128_protect(0)")
  print("ecp5wp.detect()")
  if jedec_id==b"\x9D\x60\x16":
    print("ISSI IS25LP032")
    if discard:
      sleep_ms(1000)
    is25lp128_status()
    print("write protection not supported")

detect()
