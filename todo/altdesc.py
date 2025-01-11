# TODO support altsetting interface, here is descriptor

# Strings describing memory layouts of the DFU device
# which has 2 alternate settings for FPGA and FLASH
MEMORY_LAYOUT_ALT0 = b"@FPGA/0x0/1024*4Kd"
MEMORY_LAYOUT_ALT1 = b"@FLASH/0x0/4096*4Ke"

# Notes about the dfuse string above:
# @ANY NAME/<start_address>/block[,block]
# start_address = 0x...
# block = <number>*<page_size><multiplier><memtype>
#  <number>: how many pages
#  <page_size>: self explanatory
#  <multiplier>: 'B'(ytes), 'K'(ilobytes), 'M'(egabytes)
#  <memtype>: the bottom three bits are significant:
#             writeable|erasable|readable
# 'd' is writeable
# 'e' is writeable readable
# subsequent blocks separated by commas
# Using 4K blocks: "@FLASH/0x0/1024*4Ke"

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
0x2D,
0x00,  # wTotalLength: 0x002D = 45 = (1+2+2)*9
0x01,  # bNumInterfaces
0x01,  # bConfigurationValue
0x00,  # iConfiguration
0x80,  # bmAttributes (bus powered)
0x32,  # bMaxPower
# Interface Descriptor. (alt 0)
0x09,  # bLength
0x04,  # bDescriptorType
0x00,  # bInterfaceNumber
0x00,  # bAlternateSetting
0x00,  # bNumEndpointns
0xFE,  # bInterfaceClass: application specific interface
0x01,  # bInterfaceSubClasse: device firmware update
0x02,  # bInterfaceProtocol
0x14,  # iInterface
# Device Firmware Upgrade Interface Descriptor.
0x09,  # bLength
0x21,  # bDescriptorType
0x0D,  # bmAttributes (will detach, manifestation tolerant, upload supported, download supported)
0xFF,
0x00,  # wDetatchTimeout
wTransferSize & 0xFF,
wTransferSize >> 8,  # wTransferSize
0x1A,
0x01,  # bcdDFUVersion
# Interface Descriptor. (alt 1)
0x09,  # bLength
0x04,  # bDescriptorType
0x00,  # bInterfaceNumber
0x01,  # bAlternateSetting
0x00,  # bNumEndpointns
0xFE,  # bInterfaceClass: application specific interface
0x01,  # bInterfaceSubClasse: device firmware update
0x02,  # bInterfaceProtocol
0x15,  # iInterface
# Device Firmware Upgrade Interface Descriptor.
0x09,  # bLength
0x21,  # bDescriptorType
0x0D,  # bmAttributes (will detach, manifestation tolerant, upload supported, download supported)
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
0x14: MEMORY_LAYOUT_ALT0,
0x15: MEMORY_LAYOUT_ALT1,
}
