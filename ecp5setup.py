import os

def printfile(name):
  try:
    f=open(name,"r")
    user_pass=f.read()
    print(user_pass)
    f.close()
  except:
    print("file '%s' not found." % name)

printfile("wifiman.conf")
yn=input("delete old and create new WiFi users:passwords (n/y)? ")
if yn.startswith("y"):
  f=open("wifiman.conf","w")
  f.close()
  print("all WiFi users:passwords deleted")
yn="y"
while yn.startswith("y"):
  yn=input("add WiFi user:password (n/y)? ")
  if yn.startswith("y"):
    user_pass=input("enter WiFi user:password> ")
    if user_pass.find(":")>0:
      f=open("wifiman.conf","a")
      f.write(user_pass)
      f.write("\n")
      f.close()
  printfile("wifiman.conf")

def main():
  f=open("main.py","w")
  f.write(
"try:\n"
"  import wifiman\n"
"except:\n"
"  print('wifiman.py error')\n"
"import gc\n"
"gc.collect()\n"
"import uftpd\n"
"from ntptime import settime\n"
"try:\n"
"  settime()\n"
"except:\n"
"  print('NTP not available')\n"
  )
  f.close()

yn=input("overwrite 'main.py' to run FTP server at boot (n/y)? ")
if yn.startswith("y"):
  main()
  print("main.py overwritten")

def pins_v20():
  f=open("jtagpin.py","w")
  f.write(
"# ULX3S v3.0.x or v2.x.x\n"
"tms=const(21)\n"
"tck=const(18)\n"
"tdi=const(23)\n"
"tdo=const(19)\n"
"tcknc=const(17)\n"
"led=const(5)\n"
  )
  f.close()

def pins_v31():
  f=open("jtagpin.py","w")
  f.write(
"# ULX3S v3.1.x\n"
"tms=const(5)\n"
"tck=const(18)\n"
"tdi=const(23)\n"
"tdo=const(34)\n"
"tcknc=const(21)\n"
"led=const(19)\n"
  )
  f.close()

def pins_esp32s2():
  f=open("jtagpin.py","w")
  f.write(
"# ESP32-S2 prototype\n"
"tms=const(8)\n"
"tck=const(16)\n"
"tdi=const(15)\n"
"tdo=const(7)\n"
"tcknc=const(6)\n"
"led=const(5)\n"
  )
  f.close()

def pins_fjc():
  f=open("jtagpin.py","w")
  f.write(
"# FJC-ESP32-V0r2\n"
"tms=const(4)\n"
"tck=const(16)\n"
"tdi=const(15)\n"
"tdo=const(2)\n"
"tcknc=const(21)\n"
"led=const(19)\n"
  )
  f.close()

printfile("jtagpin.py")
yn=input("change JTAG pinout (n/y)? ")
if yn.startswith("y"):
  print("0: ULX3S v3.0.x or v2.x.x")
  print("1: ULX3S v3.1.x")
  print("2: ESP32-S2 prototype")
  print("3: FJC-ESP32-V0r2")
  pinout=input("select pinout (0-3)> ")
  if pinout.startswith("0"):
    pins_v20()
  if pinout.startswith("1"):
    pins_v31()
  if pinout.startswith("2"):
    pins_esp32s2()
  if pinout.startswith("3"):
    pins_fjc()
  printfile("jtagpin.py")
