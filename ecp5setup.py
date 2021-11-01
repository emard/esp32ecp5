import os

def printfile(x):
  f=open(x,"r")
  user_pass=f.read()
  print(user_pass)
  f.close()

printfile("wifiman.conf")
yn=input("delete all existing WiFi users:passwords (y/n)? ")
if yn.startswith("y"):
  f=open("wifiman.conf","w")
  f.close()
  print("all WiFi users:passwords deleted")
yn="y"
while yn.startswith("y"):
  yn=input("add WiFi user:password (y/n)? ")
  if yn.startswith("y"):
    user_pass=input("enter WiFi user:password> ")
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
"  print('no WiFi')\n"
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

yn=input("overwrite 'main.py' to run FTP server at boot (y/n)? ")
if yn.startswith("y"):
  main()

def pins_v20():
  f=open("jtagpin.py","w")
  f.write(
"# ULX3S v2.x.x or v3.0.x\n"
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
"tms=const(21)\n"
"tck=const(18)\n"
"tdi=const(23)\n"
"tdo=const(19)\n"
"tcknc=const(17)\n"
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


yn=input("change JTAG pinout (y/n)? ")
if yn.startswith("y"):
  print("0: ULX3S v2.x.x or v3.0.x")
  print("1: ULX3S v3.1.x")
  print("2: FJC-ESP32-V0r2")
  pinout=input("select pinout (0-2)> ")
  if pinout.startswith("0"):
    pins_v20()
    print("selected pinout: ULX3S v2.x.x or v3.0.x")
  if pinout.startswith("1"):
    pins_v31()
    print("selected pinout: ULX3S v3.1.x")
  if pinout.startswith("2"):
    pins_fjc()
    print("selected pinout: FJC-ESP32-V0r2")
  printfile("jtagpin.py")
