# example main.py to connect at boot
import network
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect("accesspoint", "password")
