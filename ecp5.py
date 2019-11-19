# micropython ESP32
# ECP5 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

from time import ticks_ms, sleep_ms
from machine import SPI, Pin
from micropython import const
from struct import pack, unpack
from uctypes import addressof

class ecp5:

  def init_pinout_jtag(self):
    self.gpio_tms = const(21)
    self.gpio_tck = const(18)
    self.gpio_tdi = const(23)
    self.gpio_tdo = const(19)

  # if JTAG is directed to SD card pins
  # then bus traffic can be monitored using
  # JTAG slave OLED HEX decoder:
  # https://github.com/emard/ulx3s-misc/tree/master/examples/jtag_slave/proj/ulx3s_jtag_hex_passthru_v
  #def init_pinout_sd(self):
  #  self.gpio_tms = 15
  #  self.gpio_tck = 14
  #  self.gpio_tdi = 13
  #  self.gpio_tdo = 12


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

  # initialize both hardware accelerated SPI
  # software SPI on the same pins
  def spi_jtag_on(self):
    self.hwspi=SPI(self.spi_channel, baudrate=self.spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(self.gpio_tck), mosi=Pin(self.gpio_tdi), miso=Pin(self.gpio_tdo))
    self.swspi=SPI(-1, baudrate=self.spi_freq, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(self.gpio_tck), mosi=Pin(self.gpio_tdi), miso=Pin(self.gpio_tdo))

  def spi_jtag_off(self):
    self.hwspi.deinit()
    del self.hwspi
    self.swspi.deinit()
    del self.swspi

  def __init__(self):
    self.spi_freq = const(30000000) # Hz JTAG clk frequency
    # -1 for JTAG over SOFT SPI slow, compatibility
    #  1 or 2 for JTAG over HARD SPI fast
    #  2 is preferred as it has default pinout wired
    self.flash_write_size = const(256)
    self.flash_erase_size = const(4096) # no ESP32 memory for more at flash_loop_clever()
    flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8 } # erase commands from FLASH PDF
    self.flash_erase_cmd = flash_erase_cmd[self.flash_erase_size]
    self.spi_channel = const(2) # -1 soft, 1:sd, 2:jtag
    self.gpio_led = const(5)
    self.gpio_dummy = const(17)
    self.progress = False
    self.init_pinout_jtag()
    #self.init_pinout_sd()

  # print bytes reverse - appears the same as in SVF file
  def print_hex_reverse(self, block, head="", tail="\n"):
    print(head, end="")
    for n in range(len(block)):
      print("%02X" % block[len(block)-n-1], end="")
    print(tail, end="")

  @micropython.viper
  def bitreverse(self,x:int) -> int:
    y = 0
    for i in range(8):
        if (x >> (7 - i)) & 1:
            y |= (1 << i)
    return y
  
  @micropython.viper
  def send_tms(self, tms:int):
    if tms:
      self.tms.on()
    else:
      self.tms.off()
    self.tck.off()
    self.tck.on()

  @micropython.viper
  def send_read_data_buf(self, buf, last:int, w:ptr8):
    p = ptr8(addressof(buf))
    l = int(len(buf))
    val = 0
    self.tms.off()
    for i in range(l-1):
      byte = 0
      val = p[i]
      for nf in range(8):
        if (val >> nf) & 1:
          self.tdi.on()
        else:
          self.tdi.off()
        self.tck.off()
        self.tck.on()
        if self.tdo.value():
          byte |= 1 << nf
      if int(w):
        w[i] = byte # write byte
    byte = 0
    val = p[l-1] # read last byte
    for nf in range(7): # first 7 bits
      if (val >> nf) & 1:
        self.tdi.on()
      else:
        self.tdi.off()
      self.tck.off()
      self.tck.on()
      if self.tdo.value():
        byte |= 1 << nf
    # last bit
    if last:
      self.tms.on()
    if (val >> 7) & 1:
      self.tdi.on()
    else:
      self.tdi.off()
    self.tck.off()
    self.tck.on()
    if self.tdo.value():
      byte |= 1 << 7
    if int(w):
      w[l-1] = byte # write last byte

  @micropython.viper
  def send_data_byte_reverse(self, val:int, last:int, bits:int):
    self.tms.off()
    for nf in range(bits-1):
      if (val >> (7-nf)) & 1:
        self.tdi.on()
      else:
        self.tdi.off()
      self.tck.off()
      self.tck.on()
    if last:
      self.tms.on()
    if val & 1:
      self.tdi.on()
    else:
      self.tdi.off()
    self.tck.off()
    self.tck.on()
    
  # TAP to "reset" state
  @micropython.viper
  def reset_tap(self):
    for n in range(6):
      self.send_tms(1) # -> Test Logic Reset

  # TAP should be in "idle" state
  # TAP returns to "select DR scan" state
  @micropython.viper
  def runtest_idle(self, count:int, duration_ms:int):
    leave=int(ticks_ms()) + duration_ms
    for n in range(count):
      self.send_tms(0) # -> idle
    while int(ticks_ms()) < leave:
      self.send_tms(0) # -> idle
    self.send_tms(1) # -> select DR scan
  
  # send SIR command (bytes)
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state
  def sir(self, sir, idle=False):
    self.send_tms(1) # -> select IR scan
    self.send_tms(0) # -> capture IR
    self.send_tms(0) # -> shift IR
    self.send_read_data_buf(sir, 1, 0) # -> exit 1 IR
    self.send_tms(0) # -> pause IR
    self.send_tms(1) # -> exit 2 IR
    self.send_tms(1) # -> update IR
    if idle:
      #self.send_tms(0) # -> idle, disabled here as runtest_idle does the same
      self.runtest_idle(idle[0]+1, idle[1])
    else:
      self.send_tms(1) # -> select DR scan

  # "light" sdr can write data to "response" buffer
  # using ptr8 pointer. "response" can be same as "sdr"
  # but always take care, it is writing to "response"
  # using ptr8 pointers!
  def sdr(self, sdr, response=False, idle=False):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    if response:
      if int(len(response)) >= int(len(sdr)):
        self.send_read_data_buf(sdr, 1, addressof(response))
    else:
      self.send_read_data_buf(sdr, 1, 0) # -> exit 1 DR
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    if idle:
      #self.send_tms(0) # -> idle, disabled here as runtest_idle does the same
      self.runtest_idle(idle[0]+1, idle[1])
    else:
      self.send_tms(1) # -> select DR scan
  
  def check_response(self, response, expected, mask=0xFFFFFFFF, message=""):
    if (response & mask) != expected:
      print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

  def idcode(self):
    self.bitbang_jtag_on()
    self.led.on()
    self.reset_tap()
    self.runtest_idle(1,0)
    self.sir(b"\xE0")
    id_bytes = bytearray(4)
    self.sdr(id_bytes, response=id_bytes)
    self.led.off()
    self.bitbang_jtag_off()
    return unpack("<I", id_bytes)[0]

  # common JTAG open for both program and flash
  def common_open(self):
    self.spi_jtag_on()
    self.hwspi.init(sck=Pin(self.gpio_dummy)) # avoid TCK-glitch
    self.bitbang_jtag_on()
    self.led.on()
    self.reset_tap()
    self.runtest_idle(1,0)
    #self.sir(b"\xE0") # read IDCODE
    #self.sdr(pack("<I",0), expected=pack("<I",0), message="IDCODE")
    self.sir(b"\x1C") # LSC_PRELOAD: program Bscan register
    self.sdr(bytearray([0xFF for i in range(64)]))
    self.sir(b"\xC6") # ISC ENABLE: Enable SRAM programming mode
    self.sdr(b"\x00", idle=(2,10))
    self.sir(b"\x3C", idle=(2,1)) # LSC_READ_STATUS
    status = bytearray(4)
    self.sdr(status,response=status)
    self.check_response(unpack("<I",status)[0], mask=0x24040, expected=0, message="FAIL status")
    self.sir(b"\x0E") # ISC_ERASE: Erase the SRAM
    self.sdr(b"\x01", idle=(2,10))
    self.sir(b"\x3C", idle=(2,1)) # LSC_READ_STATUS
    status = bytearray(4)
    self.sdr(status,response=status)
    self.check_response(unpack("<I",status)[0], mask=0xB000, expected=0, message="FAIL status")
  
  # call this before sending the bitstram
  # FPGA will enter programming mode
  # after this TAP will be in "shift DR" state
  def prog_open(self):
    self.common_open()
    self.sir(b"\x46") # LSC_INIT_ADDRESS
    self.sdr(b"\x01", idle=(2,10))
    self.sir(b"\x7A") # LSC_BITSTREAM_BURST
    # ---------- bitstream begin -----------
    # manually walk the TAP
    # we will be sending one long DR command
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    # switch from bitbanging to SPI mode
    self.hwspi.init(sck=Pin(self.gpio_tck)) # 1 TCK-glitch TDI=0
    # we are lucky that format of the bitstream tolerates
    # any leading and trailing junk bits. If it weren't so,
    # HW SPI JTAG acceleration wouldn't work.
    # to upload the bitstream:
    # FAST SPI mode
    #self.hwspi.write(block)
    # SLOW bitbanging mode
    #for byte in block:
    #  self.send_data_byte_reverse(byte,0)

  # call this after uploading all of the bitstream blocks,
  # this will exit FPGA programming mode and start the bitstream
  def prog_close(self):
    # switch from hardware SPI to bitbanging
    self.hwspi.init(sck=Pin(self.gpio_dummy)) # avoid TCK-glitch
    self.bitbang_jtag_on() # 1 TCK-glitch
    self.send_tms(1) # -> exit 1 DR
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    #self.send_tms(0) # -> idle, disabled here as runtest_idle does the same
    self.runtest_idle(100, 10)
    # ---------- bitstream end -----------
    self.sir(b"\xC0", idle=(2,1)) # read usercode
    response = bytearray(4)
    self.sdr(response,response=response)
    self.check_response(unpack("<I",response)[0],expected=0,message="FAIL usercode")
    self.sir(b"\x26", idle=(2,200)) # ISC DISABLE
    self.sir(b"\xFF", idle=(2,1)) # BYPASS
    self.sir(b"\x3C") # LSC_READ_STATUS
    response = bytearray(4)
    self.sdr(response,response=response)
    status = unpack("<I",response)[0]
    self.check_response(status,mask=0x2100,expected=0x100,message="FAIL status")
    done = True
    if (status & 0x2100) != 0x100:
      done = False
    self.spi_jtag_off()
    self.reset_tap()
    self.led.off()
    self.bitbang_jtag_off()
    return done

  # call this before sending the flash image
  # FPGA will enter flashing mode
  # TAP should be in "select DR scan" state
  def flash_open(self):
    self.common_open()
    self.reset_tap()
    self.runtest_idle(1,0)
    self.sir(b"\xFF", idle=(32,0)) # BYPASS
    self.sir(b"\x3A") # LSC_PROG_SPI
    self.sdr(pack("<H",0x68FE), idle=(32,0))
    # ---------- flashing begin -----------
    # 0x60 and other SPI flash commands here are bitreverse() values
    # of flash commands found in SPI FLASH datasheet.
    # e.g. 0x1B here is actually 0xD8 in datasheet, 0x60 is is 0x06 etc.

  def flash_wait_status(self):
    retry=50
    read_status_register = pack("<H",0x00A0) # READ STATUS REGISTER
    status_register = bytearray(2)
    while retry > 0:
      self.sdr(read_status_register,response=status_register)
      if (status_register[1] & 0xC1) == 0:
        break
      sleep_ms(1)
      retry -= 1
    if retry <= 0:
      print("error write flash block, status %04X & 0xC1 != 0" % (unpack("<H",status_register))[0])
    #  self.sdr(pack("<H",0x00A0), mask=pack("<H",0xC100), expected=pack("<H",0)) # READ STATUS REGISTER

  def flash_erase_block(self, addr=0):
    self.sdr(b"\x60") # SPI WRITE ENABLE
    # some chips won't clear WIP without this:
    status = pack("<H",0x00A0) # READ STATUS REGISTER
    self.sdr(status, response=status)
    self.check_response(unpack("<H",status)[0],mask=0xC100,expected=0x4000)
    sdr = pack(">I", (self.flash_erase_cmd << 24) | (addr & 0xFFFFFF))
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.swspi.write(sdr[:-1])
    self.send_data_byte_reverse(sdr[-1],1,8) # last byte -> exit 1 DR
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.send_tms(1) # -> select DR scan
    print("from 0x%06X erase %dK" % (addr, self.flash_erase_size>>10),end="\r")
    self.flash_wait_status()

  def flash_write_block(self, block, addr=0):
    self.sdr(b"\x60") # SPI WRITE ENABLE
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    # self.bitreverse(0x40) = 0x02 -> 0x02000000
    self.swspi.write(pack(">I", 0x02000000 | (addr & 0xFFFFFF)))
    self.swspi.write(block[:-1]) # whole block except last byte
    self.send_data_byte_reverse(block[-1],1,8) # last byte -> exit 1 DR
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.send_tms(1) # -> select DR scan
    self.flash_wait_status()

  # 256-byte write block is too short for hardware SPI to accelerate
  # flash_fast_write_block() is actually slower than flash_write_block()
#  def flash_fast_write_block(self, block, addr=0):
#    self.sdr(b"\x60") # SPI WRITE ENABLE
#    self.send_tms(0) # -> capture DR
#    self.send_tms(0) # -> shift DR
#    # self.bitreverse(0x40) = 0x02 -> 0x02000000
#    # send bits of 0x02 before the TCK glitch
#    self.send_data_byte_reverse(0x02,0,7) # LSB bit 0 not sent now
#    a = pack(">I", addr)
#    self.hwspi.init(sck=Pin(self.gpio_tck)) # 1 TCK-glitch TDO=0 as LSB bit
#    self.hwspi.write(a[1:4]) # send 3-byte address
#    self.hwspi.write(block[:-1]) # whole block except last byte
#    # switch from SPI to bitbanging mode
#    self.hwspi.init(sck=Pin(self.gpio_dummy)) # avoid TCK-glitch
#    self.bitbang_jtag_on()
#    self.send_data_byte_reverse(block[-1],1,8) # last byte -> exit 1 DR
#    self.send_tms(0) # -> pause DR
#    self.send_tms(1) # -> exit 2 DR
#    self.send_tms(1) # -> update DR
#    self.send_tms(1) # -> select DR scan
#    self.flash_wait_status()

  # data is bytearray of to-be-read length
  def flash_fast_read_block(self, data, addr=0):
    # 0x0B is SPI flash fast read command
    sdr = pack(">I", 0x0B000000 | (addr & 0xFFFFFF))
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.swspi.write(sdr) # send SPI FLASH read command and address
    # fast read after address, should read 8 dummy cycles
    # this is a chance for TCK glitch workaround:
    # first 7 cycles will be done in bitbang mode
    # then switch to hardware SPI mode
    # will add 1 more TCK-glitch cycle
    for i in range(7):
      self.tck.off()
      self.tck.on()
    # switch from bitbanging to SPI mode
    self.hwspi.init(sck=Pin(self.gpio_tck)) # 1 TCK-glitch TDI=0
    self.hwspi.readinto(data) # retrieve whole block
    # switch from SPI to bitbanging mode
    self.hwspi.init(sck=Pin(self.gpio_dummy)) # avoid TCK-glitch
    self.bitbang_jtag_on()
    self.send_data_byte_reverse(0,1,8) # dummy read byte -> exit 1 DR
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.send_tms(1) # -> select DR scan

  # call this after uploading all of the flash blocks,
  # this will exit FPGA flashing mode and start the bitstream
  def flash_close(self):
    # switch from SPI to bitbanging
    # ---------- flashing end -----------
    self.sdr(b"\x20") # SPI WRITE DISABLE
    self.sir(b"\xFF", idle=(100,1)) # BYPASS
    self.sir(b"\x26", idle=(2,200)) # ISC DISABLE
    self.sir(b"\xFF", idle=(2,1)) # BYPASS
    self.sir(b"\x79") # LSC_REFRESH reload the bitstream from flash
    self.sdr(b"\x00\x00\x00", idle=(2,100))
    self.spi_jtag_off()
    self.reset_tap()
    self.led.off()
    self.bitbang_jtag_off()
    return True # FIXME
      
  def stopwatch_start(self):
    self.stopwatch_ms = ticks_ms()
  
  def stopwatch_stop(self, bytes_uploaded):
    elapsed_ms = ticks_ms() - self.stopwatch_ms
    transfer_rate_MBps = 0
    if elapsed_ms > 0:
      transfer_rate_kBps = bytes_uploaded // elapsed_ms
    print("%d bytes uploaded in %d ms (%d kB/s)" % (bytes_uploaded, elapsed_ms, transfer_rate_kBps))

  def program_loop(self, filedata, blocksize=16384):
    self.prog_open()
    bytes_uploaded = 0
    self.stopwatch_start()
    block = bytearray(blocksize)
    while True:
      if filedata.readinto(block):
        self.hwspi.write(block)
        if self.progress:
          print(".",end="")
        bytes_uploaded += len(block)
      else:
        if self.progress:
          print("*")
        break
    self.stopwatch_stop(bytes_uploaded)
    return self.prog_close()

  def open_file(self, filename, gz=False):
    filedata = open(filename, "rb")
    if gz:
      import uzlib
      return uzlib.DecompIO(filedata,31)
    return filedata

  def open_web(self, url, gz=False):
    import socket
    _, _, host, path = url.split('/', 3)
    addr = socket.getaddrinfo(host, 80)[0][-1]
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

  # data is bytearray of to-be-read length
  def flash_read(self, data, addr=0):
    self.flash_open()
    self.flash_fast_read_block(data, addr)
    self.flash_close()

  # accelerated compare flash and file block
  # return value
  # 0-must nothing, 1-must erase, 2-must write, 3-must erase and write
  @micropython.viper
  def compare_flash_file_buf(self, flash_b, file_b) -> int:
    flash_block = ptr8(addressof(flash_b))
    file_block = ptr8(addressof(file_b))
    l = int(len(file_b))
    must = 0
    for i in range(l):
      if (flash_block[i] & file_block[i]) != file_block[i]:
        must = 1
    if must: # erase will reset all bytes to 0xFF
      for i in range(l):
        if file_block[i] != 0xFF:
          must = 3
    else: # no erase
      for i in range(l):
        if flash_block[i] != file_block[i]:
          must = 2
    return must

  # clever = read-compare-erase-write
  # prevents flash wear when overwriting the same data
  # needs more buffers: 4K erase block is max that fits on ESP32
  # TODO reduce buffer usage
  def flash_loop_clever(self, filedata, addr=0):
    addr_mask = self.flash_erase_size-1
    if addr & addr_mask:
      print("addr must be rounded to flash_erase_size = %d bytes (& 0x%06X)" % (self.flash_erase_size, 0xFFFFFF & ~addr_mask))
      return
    addr = addr & 0xFFFFFF & ~addr_mask # rounded to even 64K (erase block)
    self.flash_open()
    bytes_uploaded = 0
    self.stopwatch_start()
    count_total = 0
    count_erase = 0
    count_write = 0
    file_block = bytearray(self.flash_erase_size)
    flash_block = bytearray(self.flash_erase_size)
    while filedata.readinto(file_block):
      retry = 3
      while retry >= 0:
        self.flash_fast_read_block(flash_block, addr=addr+bytes_uploaded)
        must = self.compare_flash_file_buf(flash_block,file_block)
        if must == 0:
          count_total += 1
          bytes_uploaded += len(file_block)
          break
        retry -= 1
        if must & 1: # must_erase:
          self.flash_erase_block(addr=addr+bytes_uploaded)
          count_erase += 1
        if must & 2: # must_write:
          write_addr = addr+bytes_uploaded
          block_addr = 0
          next_block_addr = 0
          while next_block_addr < len(file_block):
            next_block_addr = block_addr+self.flash_write_size
            self.flash_write_block(file_block[block_addr:next_block_addr], addr=write_addr)
            write_addr += self.flash_write_size
            block_addr = next_block_addr
          count_write += 1
        #if not verify:
        #  count_total += 1
        #  bytes_uploaded += len(file_block)
        #  break
      if retry < 0:
        break
    self.stopwatch_stop(bytes_uploaded)
    print("%dK blocks: %d total, %d erased, %d written." % (self.flash_erase_size>>10, count_total, count_erase, count_write))
    self.flash_close()
    return retry >= 0 # True if successful

# easier command typing
def idcode():
  return ecp5().idcode()

def prog(filepath):
  gz=filepath.endswith(".gz")
  if filepath.startswith("http://"):
    filedata = ecp5().open_web(filepath, gz)
  else:
    filedata = ecp5().open_file(filepath, gz)
  if filedata:
    if gz:
      return ecp5().program_loop(filedata,blocksize=4096)
    else:
      return ecp5().program_loop(filedata,blocksize=16384)
  return False

def flash(filepath, addr=0):
  gz=filepath.endswith(".gz")
  if filepath.startswith("http://"):
    filedata = ecp5().open_web(filepath, gz)
  else:
    filedata = ecp5().open_file(filepath, gz)
  if filedata:
    return ecp5().flash_loop_clever(filedata,addr)
  return False

def flash_read(addr=0, length=1):
  data = bytearray(length)
  ecp5().flash_read(data, addr)
  return data

def passthru():
  idcode = ecp5().idcode()
  if idcode != 0 and idcode != 0xFFFFFFFF:
    filepath = "passthru%08X.bit.gz" % idcode
    print("ecp5.prog(\"%s\")" % filepath)
    filedata = ecp5().open_file(filepath, gz=True)
    return ecp5().program_loop(filedata,blocksize=4096)
  return False

print("usage:")
print("ecp5.flash(\"blink.bit.gz\", addr=0x000000)")
print("ecp5.flash_read(addr=0x000000, length=1)")
print("ecp5.prog(\"http://192.168.4.2/blink.bit\")")
print("ecp5.prog(\"blink.bit.gz\") # gzip -9 blink.bit")
print("ecp5.passthru()")
print("\"0x%08X\" % ecp5.idcode()")
print("0x%08X" % idcode())
#flash("blink.bit")
#prog("blink.bit")
#prog("http://192.168.4.2/blink.bit")
