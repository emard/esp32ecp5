#!/usr/bin/env python3
import binascii

# svf.hex is only hex data from
# SDR() stream, consists only from ascii HEX and whitespaces
# use editor to prepare it

if True:
  r=open("svf.hex")
  n=open("svf.nib","wb")
  while True:
    line=bytearray(r.readline().strip().encode("utf-8"))
    if not line:
      break
    n.write(line)
  n.close()
  r.close()

n=open("svf.nib","rb")
n.seek(0,2)
size=n.tell()
w=open("svf.bit","wb")
z=bytearray(0)
i = size
buf=bytearray(2)
while i>0:
  i-=2
  n.seek(i)
  n.readinto(buf)
  #print(buf)
  a=binascii.a2b_hex(buf)
  #print(a)
  w.write(a)
  #break
  