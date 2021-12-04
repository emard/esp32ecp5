# FFC-RBP V0r10 + FJC-ESP32-V0r2 pluggable
#tms = const(4)
#tck = const(16)
#tdi = const(15)
#tdo = const(2)
#tcknc = const(21)
#led = const(19)

# ULX3S v3.0.x, v2.x.x, v1.x
tms = const(21)
tck = const(18)
tdi = const(23)
tdo = const(19)
tcknc = const(17) # free pin for SPI workaround
led = const(5)

# ULX3S v3.1.x, ULX4M + ESP32 HAT, FFC-RBP V0r12
#tms = const(5)   # BLUE LED - 549ohm - 3.3V
#tck = const(18)
#tdi = const(23)
#tdo = const(34)
#tcknc = const(21) # 1,2,3,19,21 free pin for SPI workaround
#led = const(19)

# ESP32-S2 prototype
#tms = const(8) # 38
#tck = const(16) # 36
#tdi = const(15) # 35
#tdo = const(7) # 37
#tcknc = const(12) # free pin for SPI workaround
#led = const(13)
