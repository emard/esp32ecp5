#!/usr/bin/env python3

# gzip-compress file on PC using small block size 4K,
# suitable for unzipping at devices with small RAM,
# micropython friendly

import os, sys, zlib

def gzip4k(fname):
  stream = open(fname, "rb")
  comp = zlib.compressobj(level=9, wbits=16 + 12)
  with open(fname + ".gz", "wb") as outf:
    while 1:
      data = stream.read(1024)
      if not data:
        break
      outf.write(comp.compress(data))
    outf.write(comp.flush())
  os.remove(fname)

if __name__ == "__main__":
  gzip4k(sys.argv[1])
