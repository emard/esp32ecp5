#!/usr/bin/env python3

# parse first SDR which should
# be very long, write it in reverse byte
# and byte-reverse-bits order

# usage cyclone5_svf2bit.py bitstream.svf bitstream.bit

import sys

wpos=-1
rb=bytearray(256)
def init_reverse_bits():
  global rb
  for i in range(256):
      v=i
      r=0
      for j in range(8):
        r<<=1
        r|=v&1
        v>>=1
      rb[i]=r

# write hex bytes backwards
def backwrite(dst,data):
  global wpos,rb
  for i in range(len(data)//2):
    dst[wpos]=rb[int(data[i*2:(i+1)*2],16)]
    wpos-=1

def parse():
  global wpos
  
  init_reverse_bits()
  r=open(sys.argv[1])

  l=0
  while True:
    line=bytearray(r.readline().strip().encode("utf-8"))
    if not line:
      break
    if line.startswith(b"SDR"):
      spl=line.split()
      l=int(spl[1])
      # hex stuff after "("
      data=(line.split(b"(")[1])
      break

  lb=l//8
  wpos=lb-1
  #print("length",lb,"bytes")
  bs=bytearray(lb) # bitstream allocated

  if lb:
    backwrite(bs,data)
    while True:
      line=bytearray(r.readline().strip().encode("utf-8"))
      if not line:
        break
      data=line.split(b")")
      backwrite(bs,data[0])
      if len(data)>1:
        break
  r.close()

  w=open(sys.argv[2],"wb")
  w.write(bs)
  w.close()

parse()
