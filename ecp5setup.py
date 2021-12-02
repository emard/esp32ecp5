import os

def printfile(name):
  try:
    f=open(name,"r")
    user_pass=f.read()
    print(user_pass)
    f.close()
  except:
    print("file '%s' not found." % name)

def boot():
  f=open("boot.py","w")
  f.write(
"# boot.py: executed on every boot (including wake-boot from deepsleep)\n"
"#import esp\n"
"#esp.osdebug(None)\n"
"import webrepl\n"
"webrepl.start()\n"
  )
  f.close()

def main():
  f=open("main.py","w")
  f.write(
"# main.py: executed on every boot\n"
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
"  print('NTP time set')\n"
"except:\n"
"  print('NTP not available')\n"
  )
  f.close()

def jtagpin_v20():
  f=open("jtagpin.py","w")
  f.write(
"# ULX3S v3.0.x, v2.x.x, v1.x\n"
"tms=const(21)\n"
"tck=const(18)\n"
"tdi=const(23)\n"
"tdo=const(19)\n"
"tcknc=const(17)\n"
"led=const(5)\n"
  )
  f.close()

def jtagpin_v31():
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

def jtagpin_esp32s2():
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

def jtagpin_fjc():
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

def sdpin_esp32():
  f=open("sdpin.py","w")
  f.write(
"# ESP32 SD-SPI-MMC\n"
"hiz=bytearray([2,4,12,13,14,15]) # to release SD\n"
  )
  f.close()

def sdpin_esp32s2():
  f=open("sdpin.py","w")
  f.write(
"# ESP32-S2 SD-SPI\n"
"d0=const(13)  # miso\n"
"d3=const(10)  # csn\n"
"clk=const(12) # sck\n"
"cmd=const(11) # mosi\n"
"hiz=bytearray([d0,d3,clk,cmd]) # to release SD\n"
  )
  f.close()

def set_wifi():
  print("--- WiFi ---")
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

def set_boot():
  print("--- BOOT ---")
  printfile("boot.py")
  printfile("main.py")
  yn=input("overwrite 'boot.py' and 'main.py' to run WiFi, WebREPL, NTP and FTP at boot (n/y)? ")
  if yn.startswith("y"):
    boot()
    main()
    printfile("boot.py")
    printfile("main.py")

def set_pinout():
  print("--- PINOUT ---")
  printfile("jtagpin.py")
  printfile("sdpin.py")
  yn=input("change JTAG and SD pinout (n/y)? ")
  if yn.startswith("y"):
    print("0: ULX3S v3.0.x, v2.x.x, v1.x")
    print("1: ULX3S v3.1.x")
    print("2: ESP32-S2 prototype")
    print("3: FJC-ESP32-V0r2")
    pinout=input("select pinout (0-3)> ")
    if pinout.startswith("0"):
      jtagpin_v20()
      sdpin_esp32()
    if pinout.startswith("1"):
      jtagpin_v31()
      sdpin_esp32()
    if pinout.startswith("2"):
      jtagpin_esp32s2()
      sdpin_esp32s2()
    if pinout.startswith("3"):
      jtagpin_fjc()
      sdpin_esp32()
    printfile("jtagpin.py")
    printfile("sdpin.py")

def run():
  set_wifi()
  set_boot()
  set_pinout()

run()
