# micropython ESP32
# SD card image writer

# AUTHOR=EMARD
# LICENSE=BSD

from time import ticks_ms
from machine import SPI, Pin, SDCard
from micropython import const

class sdraw:
  #def __init__(self):
    #print("SD RAW writer")
    #self.init_pinout_sd()

  def stopwatch_start(self):
    self.stopwatch_ms = ticks_ms()
  
  def stopwatch_stop(self, bytes_uploaded):
    elapsed_ms = ticks_ms() - self.stopwatch_ms
    transfer_rate_MBps = 0
    if elapsed_ms > 0:
      transfer_rate_kBps = bytes_uploaded // elapsed_ms
    print("%d bytes uploaded in %d ms (%d kB/s)" % (bytes_uploaded, elapsed_ms, transfer_rate_kBps))

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
    print("host = ",host," port = ", port, " path = ", path)
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

  def sd_open(self):
    self.sd = SDCard(slot=3)

  def sd_close(self):
    self.sd.deinit()
    for i in bytearray([2,4,12,13,14,15]):
      p=Pin(i,Pin.IN)
      a=p.value()
      del p, a
    del self.sd

  def sd_check_param(self, addr):
    if addr & 0x1FF:
      print("parameter must be rounded to block_size = 512 bytes")
      return False
    return True

  # negative addr means reference from end of the card  
  def sd_wrapaddr(self, addr):
    if addr >= 0:
      return addr
    cardsize = self.sd.ioctl(4,0)*0x200
    return cardsize+addr

  def sd_read(self, data, addr=0):
    if not self.sd_check_param(addr) or not self.sd_check_param(len(data)):
      return False
    self.sd_open()
    self.sd.readblocks(self.sd_wrapaddr(addr)//0x200,data)
    self.sd_close()
    return True

  def sd_write_stream(self, filedata, addr=0, blocksize=16384):
    if not self.sd_check_param(addr):
      return False
    bytes_uploaded = 0
    self.sd_open()
    addr=self.sd_wrapaddr(addr)
    nearend=self.sd_wrapaddr(-blocksize)
    self.stopwatch_start()
    block = bytearray(blocksize)
    while True:
      waddr=addr+bytes_uploaded
      if waddr >= nearend and len(block) > 0x200:
        block = bytearray(0x200)
      if filedata.readinto(block):
        self.sd.writeblocks(waddr//0x200,block)
        bytes_uploaded += len(block)
      else:
        break
    self.stopwatch_stop(bytes_uploaded)
    self.sd_close()
    return True

def read(addr=0, length=512):
  data = bytearray(length)
  if sdraw().sd_read(data, addr):
    return data
  else:
    return False

def write(filepath, addr=0):
  gz=filepath.endswith(".gz")
  if filepath.startswith("http://") or filepath.startswith("/http:/"):
    filedata = sdraw().open_web(filepath, gz)
  else:
    filedata = sdraw().open_file(filepath, gz)
  if filedata:
    if gz:
      return sdraw().sd_write_stream(filedata,addr,blocksize=4096)
    else:
      return sdraw().sd_write_stream(filedata,addr,blocksize=16384)
  return False

def help():
  print("usage:")
  print("sdraw.write(\"http://192.168.4.2/sdcard.img\", addr=0) # to start of SD")
  print("sdraw.read(addr=0, length=512) # from start of SD")
  print("sdraw.read(-1024) # from 1024 bytes before end of SD")
