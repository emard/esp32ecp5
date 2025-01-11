# ESP32S3 USB DFU micropython_spiram_oct >= 1.24
#
# option "--no-follow" starts the script from PC
# without waiting for a response,
# because there won't be a response,
# the default USB-serial will disconnect
# and re-enumerate as a USB-DFU device:
#
# $ mpremote run --no-follow dfu.py
# 
# apt install dfu-util
#
# write bitstream.bit to FPGA SRAM
# dfu-util -s 0:leave -D bitstream.bit

# write flash from address 0 (bootloader or user)
# dfu-util -s 0xF000000:leave -D bitstream.bit

# write flash from address 0x200000 (user)
# dfu-util -s 0xF200000:leave -D bitstream.bit

# read flash from 0x200000 length 0xE00000 to file readflash.bit
# dfu-util -s 0xF200000:0xE00000:leave -U readflash.bit

import struct, machine
import ecp5
from micropython import const

# USB constants for bmRequestType.
USB_REQ_RECIP_INTERFACE = 0x01
USB_REQ_TYPE_CLASS = 0x20
USB_DIR_OUT = 0x00
USB_DIR_IN = 0x80

# String describing the memory layout of the DFU device.
MEMORY_LAYOUT = b"@0xF000000:FLASH/0x0/61440*4Kd,4096*4Ke"

# Notes about the dfuse string above:
# /<start_address>/<number>*<page_size><multiplier><memtype>
#  <number>: how many pages
#  <page_size>: self explanatory
#  <multiplier>: 'B'(ytes), 'K'(ilobytes), 'M'(egabytes)
#  <memtype>: the bottom three bits are significant:
#             writeable|erasable|readable
# 'd' is writeable
# 'e' is writeable readable
# subsequent blocks separated by commas
# Using the internal page size: "@Internal Flash   /0x08000000/64*128Ba,448*128Bg"
# Using 1K blocks: "@Internal Flash   /0x08000000/8*001Ka,56*001Kg"

# VID and PID of the DFU device (these are the ST values).
VID = 0x1d50
PID = 0x614b

# Maximum transfer size for RX and TX.
wTransferSize = 4096

# DFU device descriptor.
_desc_dev = bytes([
0x12,  # bLength
0x01,  # bDescriptorType: Device
0x00,
0x02,  # USB version: 2.00
0x00,  # bDeviceClass
0x00,  # bDeviceSubClass
0x00,  # bDeviceProtocol
0x40,  # bMaxPacketSize
VID & 0xFF,
VID >> 8,  # VID
PID & 0xFF,
PID >> 8,  # PID
0x00,
0x01,  # bcdDevice: 1.00
0x11,  # iManufacturer
0x12,  # iProduct
0x13,  # iSerialNumber
0x01,  # bNumConfigurations: 1
])

# DFU configuration descriptor.
_desc_cfg = bytes([
# Configuration Descriptor.
0x09,  # bLength
0x02,  # bDescriptorType
0x1B,
0x00,  # wTotalLength: 27
0x01,  # bNumInterfaces
0x01,  # bConfigurationValue
0x00,  # iConfiguration
0x80,  # bmAttributes (bus powered)
0x32,  # bMaxPower
# Interface Descriptor.
0x09,  # bLength
0x04,  # bDescriptorType
0x00,  # bInterfaceNumber
0x00,  # bNumEndpointns
0x00,  # bAlternateSetting
0xFE,  # bInterfaceClass: application specific interface
0x01,  # bInterfaceSubClasse: device firmware update
0x02,  # bInterfaceProtocol
0x14,  # iInterface
# Device Firmware Upgrade Interface Descriptor.
0x09,  # bLength
0x21,  # bDescriptorType
0x0B,  # bmAttributes (will detach, upload supported, download supported)
0xFF,
0x00,  # wDetatchTimeout
wTransferSize & 0xFF,
wTransferSize >> 8,  # wTransferSize
0x1A,
0x01,  # bcdDFUVersion
])

# DFU strings.
_desc_strs = {
0x11: b"iManufacturer",
0x12: b"iProduct",
0x13: b"iSerialNumber",
0x14: MEMORY_LAYOUT,
}

# SPI FLASH
flash_read_size  = const(4096)
flash_write_size = const(256)
flash_erase_size = const(4096)

#file_block = bytearray(flash_erase_size)
#file_blockmv=memoryview(file_block)
flash_block = bytearray(flash_read_size)

# writes file_block to flash
# len(file_block) == flash_erase_size
# before: ecp5.flash_open()
# after:  ecp5.flash_close()
def flash_write_block_retry(addr, file_block):
  if len(file_block) != flash_erase_size:
    return False
  file_blockmv=memoryview(file_block)
  addr_mask = flash_erase_size-1
  if addr & addr_mask:
    # print("addr must be rounded to flash_erase_size = %d bytes (& 0x%06X)" % (flash_erase_size, 0xFFFFFF & ~addr_mask))
    return False
  addr = addr & 0xFFFFFF & ~addr_mask # rounded to even erase size
  bytes_uploaded = 0
  retry = 3
  while retry > 0:
    must = 0
    flash_rd = 0
    while flash_rd<flash_erase_size:
      ecp5.flash_read_block(flash_block,addr+bytes_uploaded+flash_rd)
      must = ecp5.compare_flash_file_buf(flash_block,file_blockmv[flash_rd:flash_rd+flash_read_size],must)
      flash_rd+=flash_read_size
    write_addr = addr+bytes_uploaded
    if must == 0:
      bytes_uploaded += len(file_block)
      break
    retry -= 1
    if must & 1: # must_erase:
      #print("from 0x%06X erase %dK" % (write_addr, flash_erase_size>>10),end="\r")
      ecp5.flash_erase_block(write_addr)
    if must & 2: # must_write:
      #print("from 0x%06X write %dK" % (write_addr, flash_erase_size>>10),end="\r")
      block_addr = 0
      next_block_addr = 0
      while next_block_addr < len(file_block):
        next_block_addr = block_addr+flash_write_size
        ecp5.flash_write_block(file_blockmv[block_addr:next_block_addr-1], file_blockmv[next_block_addr-1], write_addr)
        write_addr += flash_write_size
        block_addr = next_block_addr
    #if not verify:
    #  count_total += 1
    #  bytes_uploaded += len(file_block)
    #  break
  if retry <= 0:
    return False
  return True

# This class handles the DFU USB device logic.
class DFUOverUSB:
  def __init__(self, dfu):
    # USB buffer for transfers.
    self.usb_buf = bytearray(wTransferSize)
    # Instance of the DFU state machine.
    self.dfu = dfu

  def _control_xfer_cb(self, stage, request):
    bmRequestType, bRequest, wValue, wIndex, wLength = struct.unpack("<BBHHH", request)
    if stage == 1:  # SETUP
      if bmRequestType == USB_DIR_OUT | USB_REQ_TYPE_CLASS | USB_REQ_RECIP_INTERFACE:
        # Data coming from host, prepare to receive it.
        return memoryview(self.usb_buf)[:wLength]
      if bmRequestType == USB_DIR_IN | USB_REQ_TYPE_CLASS | USB_REQ_RECIP_INTERFACE:
        # Host requests data, prepare to send it.
        buf = memoryview(self.usb_buf)[:wLength]
        return self.dfu.handle_tx(bRequest, wValue, buf)
    elif stage == 3:  # ACK
      if bmRequestType & USB_DIR_IN:
        # EP0 TX sent.
        self.dfu.process()
      else:
        # EP0 RX ready.
        buf = memoryview(self.usb_buf)[:wLength]
        self.dfu.handle_rx(bRequest, wValue, buf)
    return True

# This class handles the DFU state machine.
class DFU:
  # DFU class requests.
  DETACH = 0
  DNLOAD = 1
  UPLOAD = 2
  GETSTATUS = 3
  CLRSTATUS = 4
  GETSTATE = 5
  ABORT = 6

  # DFU states.
  STATE_IDLE = 2
  STATE_BUSY = 4
  STATE_DNLOAD_IDLE = 5
  STATE_MANIFEST = 7
  STATE_UPLOAD_IDLE = 9
  STATE_ERROR = 0xA

  # DFU commands.
  CMD_NONE = 0
  CMD_EXIT = 1
  CMD_UPLOAD = 7
  CMD_DNLOAD = 8

  # Download sub-commands.
  CMD_DNLOAD_SET_ADDRESS = 0x21
  CMD_DNLOAD_ERASE = 0x41
  CMD_DNLOAD_READ_UNPROTECT = 0x92

  # Error status flags.
  STATUS_OK = 0x00

  def __init__(self):
    self.state = DFU.STATE_IDLE
    self.cmd = DFU.CMD_NONE
    self.status = DFU.STATUS_OK
    self.error = 0
    self.leave_dfu = False
    self.addr = 0
    self.dnload_block_num = 0
    self.dnload_len = 0
    self.dnload_buf = bytearray(wTransferSize)
    self.open = 0

  def handle_rx(self, cmd, arg, buf):
    # Handle an incoming packet of data.
    if cmd == DFU.CLRSTATUS:
      self.state = DFU.STATE_IDLE
      self.cmd = DFU.CMD_NONE
      self.status = DFU.STATUS_OK
      self.error = 0
    elif cmd == DFU.ABORT:
      self.state = DFU.STATE_IDLE
      self.cmd = DFU.CMD_NONE
      self.status = DFU.STATUS_OK
      self.error = 0
    elif cmd == DFU.DNLOAD:
      if len(buf) == 0:
        # Exit DFU.
        self.cmd = DFU.CMD_EXIT
      else:
        # Download data to device.
        self.cmd = DFU.CMD_DNLOAD
        self.dnload_block_num = arg
        self.dnload_len = len(buf)
        self.dnload_buf[: len(buf)] = buf

  def handle_tx(self, cmd, arg, buf):
    # Prepare data to go to the host.
    if cmd == DFU.UPLOAD:
      if arg >= 2 and self.addr >= 0xF000000:
        if self.open == 0:
          ecp5.flash_open()
          self.open = 1
        self.cmd = DFU.CMD_UPLOAD
        addr = (arg - 2) * flash_read_size + self.addr
        self.do_read(addr, buf)
        return buf
      return None
    elif cmd == DFU.GETSTATUS and len(buf) == 6:
      if self.cmd == DFU.CMD_NONE:
        pass
      elif self.cmd == DFU.CMD_EXIT:
        self.state = DFU.STATE_MANIFEST
      elif self.cmd == DFU.CMD_UPLOAD:
        self.state = DFU.STATE_UPLOAD_IDLE
      elif self.cmd == DFU.CMD_DNLOAD:
        self.state = DFU.STATE_BUSY
      else:
        self.state = DFU.STATE_BUSY

      # Populate the buffer to return to the host.
      buf[0] = self.status
      buf[1] = 0
      buf[2] = 0
      buf[3] = 0
      buf[4] = self.state
      buf[5] = self.error

      # Clear errors now they've been sent to host.
      self.status = DFU.STATUS_OK
      self.error = 0

      return buf
    else:
      return None

  def process(self):
    # Transition the DFU state machine.
    if self.state == DFU.STATE_MANIFEST:
      self.leave_dfu = True
      if self.open:
        if self.addr < 0xF000000:
          ecp5.prog_close()
        else:
          ecp5.flash_close()
        self.open = 0
    elif self.state == DFU.STATE_BUSY:
      if self.cmd == DFU.CMD_DNLOAD:
        self.cmd = DFU.CMD_NONE
        self.state = self.process_dnload()

  def process_dnload(self):
    ret = -1  # Assume error.
    if self.dnload_block_num == 0:
      # Download control commands.
      if self.dnload_len >= 1 and self.dnload_buf[0] == DFU.CMD_DNLOAD_ERASE:
        if self.dnload_len == 1:
          # Mass erase.
          ret = self.do_mass_erase()
          if ret != 0:
            self.cmd = DFU.CMD_NONE
        elif self.dnload_len == 5:
          # Erase page.
          addr = struct.unpack_from("<L", self.dnload_buf, 1)[0]
          ret = self.do_page_erase(addr)
      elif self.dnload_len >= 1 and self.dnload_buf[0] == DFU.CMD_DNLOAD_SET_ADDRESS:
        if self.dnload_len == 5:
          # Set address.
          self.addr = struct.unpack_from("<L", self.dnload_buf, 1)[0]
          if self.open == 0:
            if self.addr < 0xF000000:
              ecp5.prog_open()
            else:
              ecp5.flash_open()
            self.open = 1
          ret = 0
    elif self.dnload_block_num > 1:
      # Write data to memory.
      addr = (self.dnload_block_num - 2) * wTransferSize + self.addr
      ret = self.do_write(addr, self.dnload_len, self.dnload_buf)
    if ret == 0:
      return DFU.STATE_DNLOAD_IDLE
    else:
      return DFU.STATE_ERROR

  def do_mass_erase(self):
    # This function would implement a mass erase of flash memory.
    return 0  # indicate success

  def do_page_erase(self, addr):
    # This function would implement an erase of a page in flash memory.
    return 0  # indicate success

  # read block from addr of flash memory.
  def do_read(self, addr, buf):
    ecp5.flash_read_block(buf, addr & 0xFFFFFF);
    return 0  # indicate success

  # if addr < 0xF000000, write block directly to FPGA RAM
  # blocks should come sequentially for FPGA RAM
  # of addr >= 0xF000000 write block to (addr & 0xFFF000) of flash memory.
  def do_write(self, addr, size, buf):
    if self.addr < 0xF000000:
      # write to FPGA RAM bitstream
      ecp5.hwspi.write(buf[:size])
    else: # addr >= 0xF000000 write to FLASH
      flash_write_block_retry(addr & 0xFFF000, buf)
    return 0  # indicate success

# Create an instance of the DFU state machine.
dfu = DFU()

# Create an instance of the DFU USB handler.
dfu_usb = DFUOverUSB(dfu)

# Switch the USB device to the custom DFU driver.
usbd = machine.USBDevice()
usbd.active(0)
usbd.builtin_driver = usbd.BUILTIN_NONE
usbd.config(
  desc_dev=_desc_dev,
  desc_cfg=_desc_cfg,
  desc_strs=_desc_strs,
  control_xfer_cb=dfu_usb._control_xfer_cb,
)
usbd.active(1)

# Wait for the DFU state machine to complete.
#while not dfu.leave_dfu:
#    machine.idle()

# "leave" command used to run bitstream
while True:
  machine.idle()

# Switch the USB device back to the default built-in driver.
# this code seems not working correctly, mpremote won't recognize it
usbd.active(0)
usbd.builtin_driver = usbd.BUILTIN_DEFAULT
usbd.config(
  desc_dev=usbd.builtin_driver.desc_dev,
  desc_cfg=usbd.builtin_driver.desc_cfg,
  desc_strs=(),
)
usbd.active(1)
