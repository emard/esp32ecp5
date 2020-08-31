# micropython ESP32
# ARTIX7 JTAG programmer

# AUTHOR=EMARD
# LICENSE=BSD

# TODO: FLASH code here is still for ECP5.
# For ARTIX7 it should first program
# the JTAG-SPI bypass bitstream
# and then access SPI FLASH chip.

from time import ticks_ms, sleep_ms
from machine import SPI, Pin
from micropython import const
from struct import pack, unpack
from uctypes import addressof
from gc import collect

class artix7:

  def init_pinout_jtag(self):
    # FJC-ESP32-V0r2 pluggable
    #self.gpio_tms = const(4)
    #self.gpio_tck = const(16)
    #self.gpio_tdi = const(15)
    #self.gpio_tdo = const(2)
    # ESP32-WROVER-E FROGO wired
    self.gpio_tms = const(5)   # BLUE LED - 549ohm - 3.3V
    self.gpio_tck = const(18)
    self.gpio_tdi = const(23)
    self.gpio_tdo = const(34)

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
    self.spi_freq = const(20000000) # Hz JTAG clk frequency
    # -1 for JTAG over SOFT SPI slow, compatibility
    #  1 or 2 for JTAG over HARD SPI fast
    #  2 is preferred as it has default pinout wired
    self.flash_write_size = const(256)
    self.flash_erase_size = const(4096) # no ESP32 memory for more at flash_stream()
    flash_erase_cmd = { 4096:0x20, 32768:0x52, 65536:0xD8 } # erase commands from FLASH PDF
    self.flash_erase_cmd = flash_erase_cmd[self.flash_erase_size]
    self.spi_channel = const(2) # -1 soft, 1:sd, 2:jtag
    self.gpio_led = const(5)
    self.gpio_dummy = const(21)
    self.init_pinout_jtag()
    #self.init_pinout_sd()

  # print bytes reverse - appears the same as in SVF file
  #def print_hex_reverse(self, block, head="", tail="\n"):
  #  print(head, end="")
  #  for n in range(len(block)):
  #    print("%02X" % block[len(block)-n-1], end="")
  #  print(tail, end="")

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
  def send_read_data_byte(self, val:int, last:int, bits:int)->int:
    self.tms.off()
    byte = 0
    for nf in range(bits-1):
      if (val >> nf) & 1:
        self.tdi.on()
      else:
        self.tdi.off()
      self.tck.off()
      self.tck.on()
      if self.tdo.value():
        byte |= 1 << nf
    if last:
      self.tms.on()
    if (val >> (bits-1)) & 1:
      self.tdi.on()
    else:
      self.tdi.off()
    self.tck.off()
    self.tck.on()
    if self.tdo.value():
      byte |= 1 << (bits-1)
    return byte

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
  @micropython.viper
  def sir(self, sir:int)->int:
    self.send_tms(1) # -> select IR scan
    self.send_tms(0) # -> capture IR
    self.send_tms(0) # -> shift IR
    r=int(self.send_read_data_byte(sir,1,6)) # -> exit 1 IR
    self.send_tms(0) # -> pause IR
    self.send_tms(1) # -> exit 2 IR
    self.send_tms(1) # -> update IR
    self.send_tms(1) # -> select DR scan
    return r

  # send SIR command (bytes)
  # TAP should be in "select DR scan" state
  # TAP returns to "select DR scan" state
  # finish with n idle cycles during minimum of ms time
  #@micropython.viper
  #def sir_idle(self, sir:int, n:int, ms:int):
  #  self.send_tms(1) # -> select IR scan
  #  self.send_tms(0) # -> capture IR
  #  self.send_tms(0) # -> shift IR
  #  self.send_data_byte(sir,1,6) # -> exit 1 IR
  #  self.send_tms(0) # -> pause IR
  #  self.send_tms(1) # -> exit 2 IR
  #  self.send_tms(1) # -> update IR
  #  self.runtest_idle(n+1, ms) # -> select DR scan

  @micropython.viper
  def sdr(self, sdr):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.send_read_data_buf(sdr,1,0)
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.send_tms(1) # -> select DR scan

  @micropython.viper
  def sdr_idle(self, sdr, n:int, ms:int):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.send_read_data_buf(sdr,1,0)
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.runtest_idle(n+1, ms) # -> select DR scan

  # sdr buffer will be overwritten with response
  @micropython.viper
  def sdr_response(self, sdr):
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR
    self.send_read_data_buf(sdr,1,addressof(sdr))
    self.send_tms(0) # -> pause DR
    self.send_tms(1) # -> exit 2 DR
    self.send_tms(1) # -> update DR
    self.send_tms(1) # -> select DR scan

  def check_response(self, response, expected, mask=0xFFFFFFFF, message=""):
    if (response & mask) != expected:
      print("0x%08X & 0x%08X != 0x%08X %s" % (response,mask,expected,message))

  def idcode(self):
    self.bitbang_jtag_on()
    self.led.on()
    self.reset_tap()
    self.runtest_idle(1,0)
    self.sir(9)
    id_bytes = bytearray(4)
    self.sdr_response(id_bytes)
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

  # call this before sending the bitstram
  # FPGA will enter programming mode
  # after this TAP will be in "shift DR" state
  def prog_open(self):
    self.common_open()
    self.sir(0x3F) # BYPASS
    self.sir(0xB) # JPROGRAM
    self.runtest_idle(1,20)
    self.check_response(self.sir(0x14), mask=0x10, expected=0x10, message="FAIL ISC_NOOP")
    self.sir(5) # CFG_IN
    # ---------- bitstream begin -----------
    # manually walk the TAP
    # we will be sending one long DR command
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR # NOTE sent with 1 TCK glitch
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

  def prog_stream_done(self):
    # switch from hardware SPI to bitbanging done after prog_stream()
    self.hwspi.init(sck=Pin(self.gpio_dummy)) # avoid TCK-glitch
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
    self.send_tms(0) # -> idle, disabled here as runtest_idle does the same
    self.runtest_idle(1,10)
    # ---------- bitstream end -----------
    self.sir(0xC) # JSTART
    self.runtest_idle(2000,0)
    self.reset_tap()
    self.led.off()
    self.bitbang_jtag_off()
    return True

  # call this before sending the flash image
  # FPGA will enter flashing mode
  # TAP should be in "select DR scan" state
  @micropython.viper
  def flash_open(self):
    self.common_open()
    self.reset_tap()
    self.runtest_idle(1,0)
    #self.sir_idle(b"\xFF",32,0) # BYPASS
    #self.sir(b"\x3A") # LSC_PROG_SPI
    #self.sdr_idle(pack("<H",0x68FE),32,0)
    # ---------- flashing begin -----------
    # 0x60 and other SPI flash commands here are bitreverse() values
    # of flash commands found in SPI FLASH datasheet.
    # e.g. 0x1B here is actually 0xD8 in datasheet, 0x60 is is 0x06 etc.

  @micropython.viper
  def flash_wait_status(self):
    retry=50
    # read_status_register = pack("<H",0x00A0) # READ STATUS REGISTER
    status_register = bytearray(2)
    while retry > 0:
      self.sir(2) # USER1
      # always refresh status_register[0], overwitten by response
      status_register[0] = 0xA0 # 0xA0 READ STATUS REGISTER
      self.sdr_response(status_register)
      if (int(status_register[1]) & 0xC1) == 0:
        break
      sleep_ms(1)
      retry -= 1
    if retry <= 0:
      print("error flash status %04X & 0xC1 != 0" % (unpack("<H",status_register))[0])
    self.reset_tap()
    #  self.sdr(pack("<H",0x00A0), mask=pack("<H",0xC100), expected=pack("<H",0)) # READ STATUS REGISTER

  def flash_erase_block(self, addr=0):
    self.sir(2) # USER1
    self.sdr(b"\x60") # SPI WRITE ENABLE
    # some chips won't clear WIP without this:
    status = pack("<H",0x00A0) # READ STATUS REGISTER
    self.sdr_response(status)
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
    self.flash_wait_status()

  def flash_write_block(self, block, addr=0):
    self.sir(2) # USER1
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

  # data is bytearray of to-be-read length
  def flash_fast_read_block(self, data, addr=0):
    self.sir(2) # USER1
    # 0x0B is SPI flash fast read command and dummy byte read
    sdr = pack(">IB", 0x0B000000 | (addr & 0xFFFFFF),0)
    self.send_tms(0) # -> capture DR
    self.send_tms(0) # -> shift DR # NOTE sent with 1 TCK glitch
    self.hwspi.init(sck=Pin(self.gpio_tck)) # 1 TCK-glitch TDI=0
    self.hwspi.write(sdr) # send SPI FLASH read command and address
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
  @micropython.viper
  def flash_close(self):
    # switch from SPI to bitbanging
    # ---------- flashing end -----------
    self.sir(2) # USER1
    self.sdr(b"\x20") # SPI WRITE DISABLE
    self.sir(0xD) # JSHUTDOWN
    self.sir(0xB) # JPROGRAM
    self.runtest_idle(2000,20)
    self.sir(0x3F) # BYPASS
    self.runtest_idle(2000,0)
    self.spi_jtag_off()
    self.reset_tap()
    self.led.off()
    self.bitbang_jtag_off()
      
  def stopwatch_start(self):
    self.stopwatch_ms = ticks_ms()
  
  def stopwatch_stop(self, bytes_uploaded):
    elapsed_ms = ticks_ms() - self.stopwatch_ms
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
  # returns status True-OK False-Fail
  def flash_stream(self, filedata, addr=0):
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
    progress_char="."
    while filedata.readinto(file_block):
      self.led.value((bytes_uploaded >> 12)&1)
      retry = 3
      while retry >= 0:
        self.flash_fast_read_block(flash_block, addr=addr+bytes_uploaded)
        must = self.compare_flash_file_buf(flash_block,file_block)
        write_addr = addr+bytes_uploaded
        if must == 0:
          if (write_addr & 0xFFFF) == 0:
            print("\r0x%06X %dK " % (write_addr, self.flash_erase_size>>10),end="")
          else:
            print(progress_char,end="")
          progress_char="."
          count_total += 1
          bytes_uploaded += len(file_block)
          break
        retry -= 1
        if must & 1: # must_erase:
          #print("from 0x%06X erase %dK" % (write_addr, self.flash_erase_size>>10),end="\r")
          self.flash_erase_block(write_addr)
          count_erase += 1
          progress_char = "e"
        if must & 2: # must_write:
          #print("from 0x%06X write %dK" % (write_addr, self.flash_erase_size>>10),end="\r")
          block_addr = 0
          next_block_addr = 0
          while next_block_addr < len(file_block):
            next_block_addr = block_addr+self.flash_write_size
            self.flash_write_block(file_block[block_addr:next_block_addr], addr=write_addr)
            write_addr += self.flash_write_size
            block_addr = next_block_addr
          count_write += 1
          progress_char = "w"
        #if not verify:
        #  count_total += 1
        #  bytes_uploaded += len(file_block)
        #  break
      if retry < 0:
        break
    print("\r",end="")
    self.stopwatch_stop(bytes_uploaded)
    print("%dK blocks: %d total, %d erased, %d written." % (self.flash_erase_size>>10, count_total, count_erase, count_write))
    return retry >= 0 # True if successful

  def filedata_gz(self, filepath):
    gz = filepath.endswith(".gz")
    if filepath.startswith("http://") or filepath.startswith("/http:/"):
      filedata = self.open_web(filepath, gz)
    else:
      filedata = self.open_file(filepath, gz)
    return filedata, gz

# easier command typing
def idcode():
  return artix7().idcode()

def prog(filepath, prog_close=True):
  board = artix7()
  filedata, gz = board.filedata_gz(filepath)
  if filedata:
    if gz:
      board.prog_stream(filedata,blocksize=4096)
    else:
      board.prog_stream(filedata,blocksize=16384)
    # NOTE now the SD card can be released before bitstream starts
    if prog_close:
      return board.prog_close() # start the bitstream
    return True
  return False

def flash(filepath, addr=0, flash_close=True):
  board = artix7()
  filedata, gz = board.filedata_gz(filepath)
  if filedata:
    status=board.flash_stream(filedata,addr)
    # NOTE now the SD card can be released before bitstream starts
    if flash_close:
      board.flash_close() # start the bitstream
    return status
  return False

def flash_read(addr=0, length=1):
  data = bytearray(length)
  artix7().flash_read(data, addr)
  return data

def passthru():
  board = artix7()
  idcode = board.idcode()
  if idcode != 0 and idcode != 0xFFFFFFFF:
    filepath = "passthru%08X.bit.gz" % idcode
    print("artix7.prog(\"%s\")" % filepath)
    filedata = board.open_file(filepath, gz=True)
    board.prog_stream(filedata,blocksize=4096)
    return board.prog_close()
  return False

def help():
  print("usage:")
  print("artix7.flash(\"blink.bit.gz\", addr=0x000000)")
  print("artix7.flash_read(addr=0x000000, length=1)")
  print("artix7.prog(\"http://192.168.4.2/blink.bit\")")
  print("artix7.prog(\"blink.bit.gz\") # gzip -9 blink.bit")
  print("artix7.passthru()")
  print("\"0x%08X\" % artix7.idcode()")
  print("0x%08X" % idcode())

#flash("blink.bit")
#prog("blink.bit")
#prog("http://192.168.4.2/blink.bit")
collect()
