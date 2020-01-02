# example main.py to connect at boot
import network
sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    sta_if.active(True)
    sta_if.connect("accesspoint", "password")
    while not sta_if.isconnected():
            pass
print('network config:', sta_if.ifconfig())
import uftpd
