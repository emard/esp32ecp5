#!/usr/bin/env python3

# bit-reverse each byte in file (MSB-LSB mirror)

# usage cyclone5_rbf2bit.py bitstream.rbf bitstream.bit

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

def convert():
  r=open(sys.argv[1],"rb")
  w=open(sys.argv[2],"wb")

  init_reverse_bits()
  # 1-byte buffer
  b = bytearray(1)
  while r.readinto(b):
    w.write(rb[b[0]:b[0]+1])
  w.close()
  r.close()

convert()
