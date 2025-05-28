# esp32s3 micropython >= 1.24

# file browser using USB PTP protocol
# tested on linux gnome, windows 10, apple

# protocol info:
# https://github.com/gphoto/libgphoto2/tree/master/camlibs/ptp2
# git clone https://github.com/gphoto/libgphoto2
# cd libgphoto2/camlibs/ptp2
# files ptp-pack.c ptp.c ptp.h
# or ask AI for help
# https://aistudio.google.com/

# To run, just execute this file on a device with
# machine.USBDevice support,
# normal micropython binary.
# connect with usb-serial to see debug prints
#
# $ mpremote cp ptp.py :/
# $ mpremote
# >>> <enter>
# >>> <ctrl-d>
# device soft-reset
# >>> import ptp
#
# The device will then change to the custom USB device.

import machine, struct, time, os, uctypes
import ecp5
from micropython import const

# to avoid loading ftdi_sio
VID = const(0x1234)
PID = const(0xabcd)

# USB endpoints used by the device.
# interface 0
I0_EP1_IN=const(0x81)
I0_EP1_OUT=const(0x01)
I0_EP2_IN=const(0x82)

# device textual appearance
MANUFACTURER=b"iManufacturer"
PRODUCT=b"iProduct"
SERIAL=b"00000000"
CONFIGURATION=b"iConfiguration"
# if interface is named "MTP", host uses MTP protocol.
# for any other name host uses PTP protocol.
# linux gnome gvfs MTP BUG: file read doesn't work
#INTERFACE0=b"MTP" # libmtp, windows and apple
INTERFACE0=b"PTP" # libgphoto2, windows and linux
INTERFACE1=b"iInterface1"
VERSION=b"3.1.8"
STORID_VFS=const(0x10001) # micropython VFS
STORID_CUSTOM=const(0x20002) # custom for FPGA
STORAGE={STORID_VFS:b"vfs", STORID_CUSTOM:b"custom"}

EVENT_OBJECTINFO_CHANGED=False # All
#EVENT_OBJECTINFO_CHANGED=True # Windows and Linux, but not Apple

current_storid=STORID_VFS # must choose one
# PTP
# USB Still Image Capture Class defines
# debug: set all to 255 to avoid system default driver
USB_CLASS_IMAGE=const(6) # imaging
STILL_IMAGE_SUBCLASS=const(1) # still image cam
STILL_IMAGE_PROTOCOL=const(1) # cam

# Class-Specific Requests - bRequest values
STILL_IMAGE_CANCEL_REQUEST=const(0x64)
STILL_IMAGE_GET_EXT_EVENT_DATA=const(0x65)
STILL_IMAGE_DEV_RESET_REQ=const(0x66)
STILL_IMAGE_GET_DEV_STATUS=const(0x67)

# USB device descriptor.
_desc_dev = bytes([
0x12,  # 0 bLength
0x01,  # 1 bDescriptorType: Device
0x10,  # 2
0x01,  # 3 USB version: 1.10
0x00,  # 4 bDeviceClass: defined at interface level
0x00,  # 5 bDeviceSubClass
0x00,  # 6 bDeviceProtocol
0x40,  # 7 bMaxPacketSize
VID & 0xFF, # 8
VID >> 8 & 0xFF,  # 9 VID
PID & 0xFF, # 10
PID >> 8 & 0xFF,  # 11 PID
0x00,  # 12
0x07,  # 13 bcdDevice: 7.00
0x01,  # 14 iManufacturer
0x02,  # 15 iProduct
0x03,  # 16 iSerialNumber
0x01,  # 17 bNumConfigurations: 1
])

# USB configuration descriptor.
_desc_cfg = bytes([
# Configuration Descriptor.
0x09,  # 0 bLength
0x02,  # 1 bDescriptorType: configuration
0x27,  # 2
0x00,  # 3 wTotalLength: 39
0x01,  # 4 bNumInterfaces
0x01,  # 5 bConfigurationValue
0x04,  # 6 iConfiguration
0x80,  # 7 bmAttributes = Bus powered
0x96,  # 8 bMaxPower
# Interface Descriptor.
0x09,  # 0 bLength
0x04,  # 1 bDescriptorType: interface
0x00,  # 2 bInterfaceNumber
0x00,  # 3 bAlternateSetting
0x03,  # 4 bNumEndpoints
USB_CLASS_IMAGE,  # 5 bInterfaceClass = imaging
STILL_IMAGE_SUBCLASS,  # 6 bInterfaceSubClass
STILL_IMAGE_PROTOCOL,  # 7 bInterfaceProtocol
0x05,  # 8 iInterface
# Interface 0 Bulk Endpoint OUT
0x07,  # 0 bLength
0x05,  # 1 bDescriptorType: endpoint
I0_EP1_IN,  # 2 bEndpointAddress
0x02,  # 3 bmAttributes: bulk
0x40,  # 4
0x00,  # 5 wMaxPacketSize
0x00,  # 6 bInterval
# Interface 0 Bulk Endpoint IN.
0x07,  # 0 bLength
0x05,  # 1 bDescriptorType: endpoint
I0_EP1_OUT,  # 2 bEndpointAddress
0x02,  # 3 bmAttributes: bulk
0x40,  # 4
0x00,  # 5 wMaxPacketSize
0x00,  # 6 bInterval
# Interface 0 Interrupt Endpoint IN.
0x07,  # 0 bLength
0x05,  # 1 bDescriptorType: endpoint
I0_EP2_IN,  # 2 bEndpointAddress
0x03,  # 3 bmAttributes: interrupt
0x40,  # 4
0x00,  # 5 wMaxPacketSize
0x01,  # 6 bInterval
])

# USB strings.
_desc_strs = {
1: MANUFACTURER,
2: PRODUCT,
3: SERIAL,
4: CONFIGURATION,
5: INTERFACE0,
6: INTERFACE1,
}
# USB constants for bmRequestType.
USB_REQ_RECIP_INTERFACE=const(1)
USB_REQ_RECIP_DEVICE=const(0)
USB_REQ_TYPE_CLASS=const(0x20)
USB_REQ_TYPE_VENDOR=const(0x40)
USB_DIR_OUT=const(0)
USB_DIR_IN=const(0x80)

# VFS micrpython types
VFS_DIR=const(0x4000)
VFS_FILE=const(0x8000)

# PTP uctype struct
# container header
CNT_HDR_DESC = {
"len" : 0 | uctypes.UINT32,
"type": 4 | uctypes.UINT16,
"code": 6 | uctypes.UINT16,
"txid": 8 | uctypes.UINT32,
"p1"  :12 | uctypes.UINT32,
"h2"  :16 | uctypes.UINT16,
"p2"  :16 | uctypes.UINT32,
"p3"  :20 | uctypes.UINT32,
}

# some USB CTRL commands (FIXME)
SETSTATUS=const(2)
GETSTATUS=const(3)
status=bytearray([0,0,0,0,0,0])

# global PTP session ID, Transaction ID, opcode
sesid=0
txid=0

# global sendobject (receive file) length
send_parent=0 # to which directory we will send object
send_parent_path="/"
send_length=0
remaining_send_length=0
remain_getobj_len=0
addr=0
fd=None # local open file descriptor

# for ls() generating vfs directory tree
# global handle incremented
# next handle must start for 0 to assign
# root with 0. if next_handle!=0 vfs will
# appear as empty
next_handle=0
current_send_handle=0

# simplified structure
# object handle->path and path->object handle
# caches for every os.ilistdir object
# pre-filled with custom fs items
# NOTE for root level objects returned
# parent object id must be 0 in each storage
# but we can't have both 0:"/vfs/" and 0:"/custom/"
# ls("/vfs/") will overwrite oh2path[0]="/vfs/" but
# path2oh["/custom/"]=0 will remain
oh2path={
0:"/custom/",
0xc10000d1:"/custom/fpga/",
0xc10000f1:"/custom/fpga/fpga.bit.txt",
0xc20000d2:"/custom/flash/",
0xc20000f2:"/custom/flash/flash.bin.txt",
}
# path2oh is reverse of oh2path, only file names
path2oh={v:k for k,v in oh2path.items()}

# current ilistdir, pre-filled with custom fs
# { 1:('main.py',32768,0,123), 2:('lib',16384,0,0), }
cur_list={}
# object id of current parent directory
cur_parent=0

custom_txt=b"copy binary file to this directory\n"

# fuxed custom ilistdir, pre-filled with custom fs
fix_custom_cur_list={
0:{
  0xc10000d1:('fpga',VFS_DIR,0,0),
  0xc20000d2:('flash',VFS_DIR,0,0),
  },
0xc10000d1:{0xc10000f1:('fpga.bit.txt',VFS_FILE,0,len(custom_txt))},
0xc20000d2:{0xc20000f2:('flash.bin.txt',VFS_FILE,0,len(custom_txt))},
}

# USB PTP "type" 16-bit field
PTP_USB_CONTAINER_UNDEFINED=const(0)
PTP_USB_CONTAINER_COMMAND=const(1)
PTP_USB_CONTAINER_DATA=const(2)
PTP_USB_CONTAINER_RESPONSE=const(3)
PTP_USB_CONTAINER_EVENT=const(4)

# response codes, more in libgphoto2 ptp.h
PTP_RC_OK=const(0x2001)
#PTP_RC_GeneralError=const(0x2002)
#PTP_RC_StoreFull=const(0x200C)
#PTP_RC_ObjectWriteProtected=const(0x200D)
#PTP_RC_InvalidCodeFormat=const(0x2016)
#PTP_RC_UnknownVendorCode=const(0x2017)
#PTP_RC_InvalidDataSet=const(0x2023)

length_response=bytearray(1) # length to send response once
send_response=bytearray(32) # response to send

length_irq_response=bytearray(1) # length to send response once
send_irq_response=bytearray(32) # interrupt response to send

# strip 1 directory level from
# left slide (first level after root)
# skip storage name so "/vfs/" becomes "/"
def strip1dirlvl(path:str)->str:
  return path[path.find("/",1):]

# list directory items
# update internal cache path -> object id
# cache obtained list of objects for later use
# path is directory with trailing slash
# recurse in number of subdirs to descend
def ls(path:str):
  global next_handle,cur_parent,cur_list
  try:
    dir=os.ilistdir(strip1dirlvl(path))
  except:
    return
  if path in path2oh:
    cur_parent=path2oh[path]
  else:
    cur_parent=next_handle
    next_handle+=1
    path2oh[path]=cur_parent
    oh2path[cur_parent]=path
  cur_list={}
  for obj in dir:
    if obj[1]==VFS_FILE:
      objname=obj[0]
    if obj[1]==VFS_DIR:
      objname=obj[0]+"/"
    fullpath=path+objname
    if fullpath in path2oh:
      oh=path2oh[fullpath]
    else:
      oh=next_handle
      next_handle+=1
      path2oh[fullpath]=oh
      oh2path[oh]=fullpath
    cur_list[oh]=obj
    #print(oh,fullpath,obj)

# for a given object id return
# its parent directory
def parent(oh:int)->int:
  path=oh2path[oh]
  pp=path[:path[:-1].rfind("/")+1]
  return path2oh[pp]

def print_ptp_header(cnt):
  print("%08x %04x %04x %08x" % struct.unpack("<LHHL",cnt),end="")

def print_ptp_params(cnt):
  for i in range((len(cnt)-12)//4):
    print("p%d:%08x" % (i,struct.unpack("<L",cnt[12+4*i:16+4*i])[0]))

def print_ptp(cnt):
  print_ptp_header(cnt)
  print_ptp_params(cnt)

def print_hex(cnt):
  print_ptp_header(cnt)
  for x in cnt[12:]:
    print(" %02x" % x,end="")
  print("")

def print_hexdump(cnt):
  for x in cnt:
    print(" %02x" % x,end="")
  print("")

def print_ucs2_string(s):
  #l,=struct.unpack("<B",s[0])
  for i in range(s[0]):
    print("%c" % s[1+i+i],end="")
  print("")

# pack a tuple as 16-bit array for deviceinfo
def uint16_array(a):
  return struct.pack("<L"+"H"*len(a),len(a),*a)

# pack a bytearray string as 16-bit ucs2 string for device info
def ucs2_string(b):
  if len(b):
    return struct.pack("<B"+"H"*(len(b)+1),len(b)+1,*b,0)
  return b"\0"

def decode_ucs2_string(s):
  len=s[0]
  str=bytearray(len)
  for i in range(len):
    str[i]=s[1+i+i]
  return str

def get_ucs2_string(s):
  len=s[0]
  return s[0:1+len+len]

# objecthandle array
def uint32_array(a):
  return struct.pack("<L"+"L"*len(a),len(a),*a)

# for immediate response IN "ok"
def hdr_ok():
  hdr.len=12
  hdr.type=PTP_USB_CONTAINER_RESPONSE
  hdr.code=PTP_RC_OK
  return 12

def in_hdr_ok():
  hdr_ok()
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:hdr.len])

def in_ok_sendobject():
  hdr.len=24
  hdr.type=PTP_USB_CONTAINER_RESPONSE
  hdr.code=PTP_RC_OK
  hdr.txid=txid
  hdr.p1=current_storid
  hdr.p2=send_parent
  hdr.p3=current_send_handle
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:hdr.len])

# after one IN submit another with response OK
def respond_ok():
  send_response[0:12]=struct.pack("<LHHL",12,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK,hdr.txid)
  length_response[0]=12
  # length_response[0] is set now and reset to 0 after IN is submitted

def respond_ok_tx(id):
  send_response[0:12]=struct.pack("<LHHL",12,PTP_USB_CONTAINER_RESPONSE,PTP_RC_OK,id)
  length_response[0]=12

def in_hdr_data(data):
  hdr.len=12+len(data)
  hdr.type=PTP_USB_CONTAINER_DATA
  i0_usbd_buf[12:hdr.len]=data
  #print(">",end="")
  #print_hex(i0_usbd_buf[:hdr.len])
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:hdr.len])

def OpenSession(cnt):
  global sesid
  sesid=hdr.p1
  in_hdr_ok()

# event codes, more in libgphoto2 ptp.h
PTP_EC_CancelTransaction=const(0x4001)
PTP_EC_ObjectInfoChanged=const(0x4007)

# device properties
PTP_DPC_DateTime=const(0x5011)
# file formats
PTP_OFC_Undefined=const(0x3000)
PTP_OFC_Directory=const(0x3001)
#PTP_OFC_Defined=const(0x3800)
#PTP_OFC_Executable=const(0x3003)
PTP_OFC_Text=const(0x3004)
#PTP_OFC_HTML=const(0x3005)
#PTP_OFC_WAV=const(0x3008)
#PTP_OFC_EXIF_JPEG=const(0x3801)
#PTP_OFC_BMP=const(0x3804)
#PTP_OFC_Undefined_0x3806=const(0x3806)
#PTP_OFC_GIF=const(0x3807)
#PTP_OFC_JFIF=const(0x3808)
#PTP_OFC_PNG=const(0x380B)
#PTP_OFC_Undefined_0x380C=const(0x380C)
#PTP_OFC_TIFF=const(0x380D)

def GetDeviceInfo(cnt): # 0x1001
  # prepare response: device info standard 1.00 = 100
  header=struct.pack("<HLH",100,0,100)
  extension=b"\0"
  #extension=ucs2_string(b"android.com")
  functional_mode=struct.pack("<H", 0) # 0: standard mode
  # unique lower 16-bit keys from ptp_opcode_cb.keys()
  #operations=uint16_array(set([code&0xFFFF for code in list((ptp_opcode_cb.keys()))])) # human readable
  #operations=uint16_array(set([code&0xFFFF for code in ptp_opcode_cb])) # short of previous line, set filters unique only
  operations=uint16_array(ptp_opcode_cb) # short of previous line, set filters unique only
  events=uint16_array((PTP_EC_ObjectInfoChanged,))
  #deviceprops=uint16_array((PTP_DPC_DateTime,))
  deviceprops=uint16_array(())
  captureformats=uint16_array(())
  #captureformats=uint16_array((PTP_OFC_EXIF_JPEG,))
  imageformats=uint16_array((
  PTP_OFC_Undefined,
  PTP_OFC_Directory,
  PTP_OFC_Text,
  #PTP_OFC_HTML,
  #PTP_OFC_EXIF_JPEG,
  #PTP_OFC_WAV,
  #PTP_OFC_Defined,
  ))
  manufacturer=ucs2_string(MANUFACTURER)
  model=ucs2_string(PRODUCT)
  deviceversion=ucs2_string(VERSION)
  serialnumber=ucs2_string(SERIAL)
  data=header+extension+functional_mode+operations+events+deviceprops+captureformats+imageformats+manufacturer+model+deviceversion+serialnumber
  respond_ok()
  in_hdr_data(data)

def GetStorageIDs(cnt): # 0x1004
  data=uint32_array(STORAGE)
  respond_ok()
  in_hdr_data(data)

# PTP_si_StorageType               0
# PTP_si_FilesystemType            2
# PTP_si_AccessCapability          4
# PTP_si_MaxCapability             6
# PTP_si_FreeSpaceInBytes         14
# PTP_si_FreeSpaceInImages        22
# PTP_si_StorageDescription       26

# Storage Types
STORAGE_FIXED_RAM=const(1)
STORAGE_REMOVABLE_RAM=const(2)
STORAGE_REMOVABLE_ROM=const(3)
STORAGE_FIXED_ROM=const(4)
STORAGE_REMOVABLE_MEDIA=const(5)
STORAGE_FIXED_MEDIA=const(6)

# Filesystem Access Capability
STORAGE_READ_WRITE=const(0)
STORAGE_READ_ONLY_WITHOUT_DELETE=const(1)
STORAGE_READ_ONLY_WITH_DELETE=const(2)

def GetStorageInfo(cnt): # 0x1005
  storageid=hdr.p1
  #print("storageid 0x%08x" % storageid)
  StorageType=STORAGE_FIXED_MEDIA
  FilesystemType=2
  AccessCapability=STORAGE_READ_WRITE
  storinfo=os.statvfs("/")
  blksize=storinfo[0]
  blkmax=storinfo[2]
  blkfree=storinfo[3]
  MaxCapability=blksize*blkmax
  FreeSpaceInBytes=blksize*blkfree
  FreeSpaceInImages=0x10000
  StorageDescription=ucs2_string(STORAGE[storageid])
  VolumeLabel=StorageDescription # for Apple
  hdr1=struct.pack("<HHHQQL",StorageType,FilesystemType,AccessCapability,MaxCapability,FreeSpaceInBytes,FreeSpaceInImages)
  data=hdr1+StorageDescription+VolumeLabel
  respond_ok()
  in_hdr_data(data)

# for given handle id of a directory
# returns array of handles
def GetObjectHandles(cnt): # 0x1007
  global cur_list
  storageid=hdr.p1
  #print("storageid 0x%08x" % storageid)
  if storageid==0xFFFFFFFF:
    # return empty storage
    respond_ok()
    data=uint32_array([])
    in_hdr_data(data)
    return
  dirhandle=hdr.p3
  if dirhandle==0xFFFFFFFF: # root directory
    dirhandle=0
  if storageid==STORID_VFS:
    if dirhandle==0:
      ls("/vfs/")
    else:
      ls(oh2path[dirhandle])
  if storageid==STORID_CUSTOM:
    cur_list=fix_custom_cur_list[dirhandle]
  data=uint32_array(cur_list)
  # FIXME when directory has many entries > 256 data
  # would not fit in one 4160 byte block
  # block continuation neede
  respond_ok()
  in_hdr_data(data)

# PTP_oi_StorageID		 0
# PTP_oi_ObjectFormat		 4
# PTP_oi_ProtectionStatus        6
# PTP_oi_ObjectSize		 8
# PTP_oi_ThumbFormat		12
# PTP_oi_ThumbSize		14
# PTP_oi_ThumbPixWidth		18
# PTP_oi_ThumbPixHeight		22
# PTP_oi_ImagePixWidth		26
# PTP_oi_ImagePixHeight		30
# PTP_oi_ImageBitDepth		34
# PTP_oi_ParentObject           38
# PTP_oi_AssociationType        42
# PTP_oi_AssociationDesc        44
# PTP_oi_SequenceNumber		48
# PTP_oi_filenamelen		52
# PTP_oi_Filename               53

def GetObjectInfo(cnt): # 0x1008
  global cur_list
  objh=hdr.p1 # FIXME optimize code
  # if object handle has different parent
  # it is probably not in cur_list, so
  # update cur_list with ls(parent)
  this_parent=parent(objh)
  if this_parent in oh2path:
    if this_parent!=cur_parent:
      if objh>>28: # custom
        cur_list=fix_custom_cur_list[this_parent]
      else: # vfs
        ls(oh2path[this_parent])
  #print("objh=%08x" % objh)
  ObjectFormat=PTP_OFC_Text
  ProtectionStatus=0 # 0:rw 1:ro
  thumb_image_null=bytearray(26)
  assoc_seq_null=bytearray(10)
  if objh in oh2path:
    fullpath=oh2path[objh]
    ParentObject=parent(objh) # 0 means this file is in root directory
    if objh>>28: # member of custom fs
      StorageID=STORID_CUSTOM
      objname,objtype,_,objsize=fix_custom_cur_list[ParentObject][objh]
    else: # high nibble=0 vfs
      StorageID=STORID_VFS
      objname,objtype,_,objsize=cur_list[objh]
    #objtype,_,_,_,_,_,objsize,_,_,_=os.stat(fullpath)
    #objname=fullpath[fullpath.rfind("/")+1:]
    #objname=basename(objh)
    #if fullpath[-1]=="/": # dir
    if objtype==VFS_DIR: # dir
      ObjectFormat=PTP_OFC_Directory
      ObjectSize=0
    else: # stat[0]==VFS_FILE # file
      ObjectFormat=PTP_OFC_Text
      ObjectSize=objsize
    hdr1=struct.pack("<LHHL",StorageID,ObjectFormat,ProtectionStatus,ObjectSize)
    hdr2=struct.pack("<L",ParentObject)
    #print("objname:",objname)
    name=ucs2_string(objname.encode()) # directory name converted
    #year, month, day, hour, minute, second, weekday, yearday = time.localtime()
    # create/modify report as current date (file constantly changes date)
    create=b"\0" # if we don't provide file time info
    #create=ucs2_string(b"%04d%02d%02dT%02d%02d%02d" % (year,month,day,hour,minute,second))
    #create=ucs2_string(b"20250425T100120") # 2025-04-25 10:01:20
    modify=create
    #data=hdr1+thumb_image_null+hdr2+assoc_seq_null+name+b"\0\0\0"
    data=hdr1+thumb_image_null+hdr2+assoc_seq_null+name+create+modify+b"\0"
    respond_ok()
    in_hdr_data(data)

def GetObject(cnt): # 0x1009
  global txid,remain_getobj_len,fd
  txid=hdr.txid
  if hdr.p1 in oh2path:
    fullpath=oh2path[hdr.p1]
    #print(fullpath)
    if fullpath.startswith("/vfs"):
      fd=open(strip1dirlvl(fullpath),"rb")
      filesize=fd.seek(0,2)
      fd.seek(0)
      len1st=fd.readinto(memoryview(i0_usbd_buf)[12:])
      # file data after 12-byte header
      length=12+len1st
      remain_getobj_len=filesize-len1st
      if remain_getobj_len<=0:
        remain_getobj_len=0
        fd.close()
        respond_ok_tx(txid)
    if fullpath.startswith("/custom"):
      msg=custom_txt
      filesize=len(msg)
      length=12+filesize
      remain_getobj_len=0
      memoryview(i0_usbd_buf)[12:12+len(msg)]=msg
      respond_ok_tx(txid)
    hdr.len=12+filesize
    hdr.type=PTP_USB_CONTAINER_DATA
  usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:length])

def DeleteObject(cnt): # 0x100B
  fullpath=oh2path[hdr.p1]
  del(oh2path[hdr.p1])
  if hdr.p1 in cur_list:
    del(cur_list[hdr.p1])
  del(path2oh[fullpath])
  if hdr.p1>>28==0: # VFS
    os.unlink(strip1dirlvl(fullpath))
  #print("deleted",fullpath)
  in_hdr_ok()

def SendObjectInfo(cnt): # 0x100C
  global txid,send_length,send_name,next_handle,current_send_handle
  global send_parent,send_parent_path,send_fullpath
  global current_storid
  txid=hdr.txid
  if hdr.type==PTP_USB_CONTAINER_COMMAND: # 1
    storageid=hdr.p1
    #print("storageid 0x%08x" % storageid)
    current_storid=storageid
    #send_parent,=struct.unpack("<L",cnt[16:20])
    send_parent=hdr.p2
    if send_parent==0xffffffff:
      send_parent=0
    #print("send_parent: 0x%x" % send_parent)
    send_parent_path=oh2path[send_parent]
    #print("send dir path",send_parent_path)
    # prepare full buffer to read from host again
    # host will send another OUT
    usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)
  if hdr.type==PTP_USB_CONTAINER_DATA: # 2
    # we just have received data from host
    # host sends in advance file length to be sent
    send_objtype=hdr.h2
    #print("send objtype 0x%04x" % send_objtype)
    send_name=get_ucs2_string(cnt[64:])
    str_send_name=decode_ucs2_string(send_name)[:-1].decode()
    #print("send name:", str_send_name)
    #send_length,=struct.unpack("<L", cnt[20:24])
    send_length=hdr.p3
    #print("send length:", send_length)
    send_fullpath=oh2path[send_parent]+str_send_name
    #print("fullpath",send_fullpath)
    if send_fullpath in path2oh:
      current_send_handle=path2oh[send_fullpath]
    else:
      # HACK copy parent's upper byte, used for custom fs
      # for objects to keep bits 31:24 of parent id in
      # bits 31:24 of new handle id
      current_send_handle=next_handle|(send_parent&0xFF000000)
      next_handle+=1
      #str_send_name_p2h=str_send_name
      send_fullpath_h2p=send_fullpath
      vfstype=VFS_FILE
      if send_objtype==PTP_OFC_Directory: # new dir
        vfstype=VFS_DIR
        #str_send_name_p2h+="/"
        send_fullpath_h2p+="/"
        os.mkdir(strip1dirlvl(send_fullpath))
      path2oh[send_fullpath_h2p]=current_send_handle
      oh2path[current_send_handle]=send_fullpath_h2p
      if current_send_handle>>28: # !=0 custom
        fix_custom_cur_list[send_parent][current_send_handle]=(str_send_name,vfstype,0,send_length)
      else: # ==0 vfs
        cur_list[current_send_handle]=(str_send_name,vfstype,0,send_length)
      #path2handle[send_parent_path][str_send_name_p2h]=current_send_handle
      #handle2path[current_send_handle]=send_fullpath_h2p
    vfs_objtype=VFS_FILE # default is file
    if send_objtype==PTP_OFC_Directory:
      vfs_objtype=VFS_DIR # directory
    #dir2handle[send_parent][current_send_handle]=(str_send_name,vfs_objtype,0,send_length)
    #print("current send handle",current_send_handle)
    # send OK response to host
    hdr_ok()
    # extend "OK" response with 3 addional 32-bit fields:
    # storage_id, parend_id, object_id
    hdr.len=24
    hdr.p1=current_storid
    hdr.p2=send_parent
    hdr.p3=current_send_handle
    #print(">",end="")
    #print_hex(i0_usbd_buf[:hdr.len])
    usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:hdr.len])

def irq_sendobject_complete():
  global fd
  hdr.len=16
  hdr.type=PTP_USB_CONTAINER_EVENT
  hdr.code=PTP_EC_ObjectInfoChanged
  hdr.p1=current_send_handle
  print("irq>",end="")
  print_hex(i0_usbd_buf[:hdr.len])
  usbd.submit_xfer(I0_EP2_IN, memoryview(i0_usbd_buf)[:hdr.len])

def close_sendobject():
  if send_parent>>24==0xc1: # fpga
    ecp5.prog_close()
  elif send_parent>>24==0xc2: # flash
    ecp5.flash_close()
  else:
    fd.close()

def SendObject(cnt): # 0x100D
  global txid,send_length,remaining_send_length,addr,fd
  txid=hdr.txid
  if hdr.type==PTP_USB_CONTAINER_COMMAND: # 1
    if send_parent>>24==0xc1: # fpga
      ecp5.prog_open()
    elif send_parent>>24==0xc2: # flash
      ecp5.flash_open()
      addr=0
    else:
      fd=open(strip1dirlvl(send_fullpath),"wb")
    # host will send another OUT command
    # prepare full buffer to read again from host
    usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)
  if hdr.type==PTP_USB_CONTAINER_DATA: # 2
    # host has just sent data
    # 12 bytes header, rest is payload
    if send_length>0:
      if send_parent>>24==0xc1: # fpga
        ecp5.hwspi.write(cnt[12:])
      elif send_parent>>24==0xc2: # flash
        # first packet is read in 4160=4096+64 bytes buffer
        # buf[0:12] header
        # buf[12:4108] 4096 bytes flash
        # buf[4108:4160] 52 bytes of next flash payload
        # pad with 0xFF if flash shorter than 4096
        # after flashing first block, copy buf[4108:4160] to buf[0:52]
        # schecule read of every next packet 4096 bytes to buf[52:4148]
        # flash buf[0:4096]
        # copy buf[4096:4148] to buf[0:52]
        # last packet: pad with 0xFF if shorter than 4096
        if len(cnt)<4108:
          memoryview(i0_usbd_buf)[len(cnt):4108]=bytearray(b"\xff"*(4108-len(cnt)))
        ecp5.flash_write_block_retry(memoryview(i0_usbd_buf)[12:4108],addr&0xFFF000)
        memoryview(i0_usbd_buf)[:52]=i0_usbd_buf[4108:4160]
        addr+=4096
      else:
        fd.write(cnt[12:])
      remaining_send_length=send_length-(len(cnt)-12)
      send_length=0
    #print("send_length=",send_length,"remain=",remaining_send_length)
    # if host has sent all bytes it promised to send
    # report it to the host that file is complete
    if remaining_send_length<=0:
      # send irq, after irq reply OK to host
      #print(">",end="")
      #print_hex(i0_usbd_buf[:length])
      close_sendobject()
      if EVENT_OBJECTINFO_CHANGED:
        irq_sendobject_complete()
      else:
        in_ok_sendobject()
    else:
      # host will send another OUT command
      # prepare full buffer to read again from host
      if send_parent>>24==0xc2: # flash
        usbd.submit_xfer(I0_EP1_OUT,memoryview(i0_usbd_buf)[52:4148])
      else:
        usbd.submit_xfer(I0_EP1_OUT,i0_usbd_buf)

#def SetObjectProtection(cnt): # 0x1012
#  # hdr.p1 objecthandle
#  # hdr.p2 0:rw 1:ro
#  in_hdr_ok()

def CloseSession(cnt): # 0x1007
  in_hdr_ok()

# callback functions for opcodes
# more in libgphoto2 ptp.h and ptp.c
ptp_opcode_cb = {
  0x1001:GetDeviceInfo,
  0x1002:OpenSession,
  0x1003:CloseSession,
  0x1004:GetStorageIDs,
  0x1005:GetStorageInfo,
  0x1007:GetObjectHandles,
  0x1008:GetObjectInfo,
  0x1009:GetObject,
  0x100B:DeleteObject,
  0x100C:SendObjectInfo,
  0x100D:SendObject,
  #0x1012:SetObjectProtection,
}

# EP0 control requests handlers
def handle_out(bRequest, wValue, buf):
  if bRequest == SETSTATUS and len(buf) == 6:
    status[0:6]=buf[0:6]

def handle_in(bRequest, wValue, buf):
  if bRequest == GETSTATUS and len(buf) == 6:
    buf[0:6]=status[0:6]
  return buf

# buf for control transfers
usb_buf = bytearray(64)

# USB data buffer for Bulk IN and OUT transfers.
# must be multiple of 64 bytes
i0_usbd_buf = bytearray(4160)

# fixed parsed ptp header
hdr=uctypes.struct(uctypes.addressof(i0_usbd_buf),CNT_HDR_DESC,uctypes.LITTLE_ENDIAN)

# not used
# on linux device works without supporting
# any of the control transfers
def _control_xfer_cb(stage, request):
  #print("_control_xfer_cb", stage, bytes(request))
  bmRequestType, bRequest, wValue, wIndex, wLength = struct.unpack("<BBHHH", request)
  if stage == 1:  # SETUP
    if bmRequestType == USB_DIR_OUT | USB_REQ_TYPE_CLASS | USB_REQ_RECIP_DEVICE:
      # Data coming from host, prepare to receive it.
      return memoryview(usb_buf)[:wLength]
    elif bmRequestType == USB_DIR_IN | USB_REQ_TYPE_CLASS | USB_REQ_RECIP_DEVICE:
      # Host requests data, prepare to send it.
      buf = memoryview(usb_buf)[:wLength]
      return handle_in(bRequest, wValue, buf) # return None or buf

  elif stage == 3:  # ACK
    if bmRequestType & USB_DIR_IN:
      # EP0 TX sent.
      a=1 # process something
    else:
      # EP0 RX ready.
      buf = memoryview(usb_buf)[:wLength]
      handle_out(bRequest,wValue,buf)
  return True

# USB callback when our custom USB interface is opened by the host.
def _open_itf_cb(interface_desc_view):
  # Prepare to receive first data packet on the OUT endpoint.
  if interface_desc_view[11] == I0_EP1_IN:
    usbd.submit_xfer(I0_EP1_OUT,i0_usbd_buf)
  #print("_open_itf_cb", bytes(interface_desc_view))

def ep1_out_done(result, xferred_bytes):
  global remaining_send_length,addr,fd
  if remaining_send_length>0:
    # continue receiving parts of the file
    if send_parent>>24==0xc1:
      ecp5.hwspi.write(i0_usbd_buf)
    elif send_parent>>24==0xc2: # flash
      if xferred_bytes<4096:
        memoryview(i0_usbd_buf)[52+xferred_bytes:4148]=bytearray(b"\xff"*(4096-xferred_bytes))
      ecp5.flash_write_block_retry(memoryview(i0_usbd_buf)[:4096],addr&0xFFF000)
      memoryview(i0_usbd_buf)[:52]=i0_usbd_buf[4096:4148]
      addr+=xferred_bytes
    else:
      fd.write(i0_usbd_buf[:xferred_bytes])
    remaining_send_length-=xferred_bytes
    #print_hexdump(cnt)
    #print("<len(cnt)=",xferred_bytes,"remaining_send_length=", remaining_send_length)
    if remaining_send_length>0:
      # host will send another OUT command
      # prepare full buffer to read again from host
      if send_parent>>24==0xc2: # flash
        usbd.submit_xfer(I0_EP1_OUT, memoryview(i0_usbd_buf)[52:4148])
      else:
        usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)
    else:
      # signal to host we have received entire file
      close_sendobject()
      if EVENT_OBJECTINFO_CHANGED:
        irq_sendobject_complete()
      else:
        in_ok_sendobject()
  else:
    #print("0x%04x %s" % (hdr.code,ptp_opcode_cb[hdr.code].__name__))
    #print("<",end="")
    #print_hex(i0_usbd_buf[:xferred_bytes])
    ptp_opcode_cb[hdr.code](i0_usbd_buf[:xferred_bytes])

def ep1_in_done(result, xferred_bytes):
  global remain_getobj_len,fd
  # prepare full buffer to read for next host OUT command
  if length_response[0]:
    #print(">",end="")
    #print_hex(send_response[:length_response[0]])
    usbd.submit_xfer(I0_EP1_IN, send_response[:length_response[0]])
    length_response[0]=0 # consumed, prevent recurring
  else:
    if remain_getobj_len:
      #print("remain_getobj_len",remain_getobj_len)
      # TODO flash reading
      packet_len=fd.readinto(i0_usbd_buf)
      remain_getobj_len-=packet_len
      if remain_getobj_len<=0:
        remain_getobj_len=0
        fd.close()
        respond_ok_tx(txid) # after this send ok IN response
      #print(">",end="")
      #print_hexdump(i0_usbd_buf[:packet_len])
      usbd.submit_xfer(I0_EP1_IN, memoryview(i0_usbd_buf)[:packet_len])
    else:
      usbd.submit_xfer(I0_EP1_OUT, i0_usbd_buf)

def ep2_in_done(result, xferred_bytes):
  # after IRQ data being sent, reply OK to host
  in_ok_sendobject()

ep_addr_cb = {
  I0_EP1_OUT:ep1_out_done,
  I0_EP1_IN:ep1_in_done,
  I0_EP2_IN:ep2_in_done
}

def _xfer_cb(ep_addr,result,xferred_bytes):
  ep_addr_cb[ep_addr](result,xferred_bytes)

# Switch the USB device to our custom USB driver.
usbd = machine.USBDevice()
usbd.builtin_driver = usbd.BUILTIN_NONE
usbd.config(
  desc_dev=_desc_dev,
  desc_cfg=_desc_cfg,
  desc_strs=_desc_strs,
  control_xfer_cb=_control_xfer_cb,
  open_itf_cb=_open_itf_cb,
  xfer_cb=_xfer_cb,
)
usbd.active(1)
