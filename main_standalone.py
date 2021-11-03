# example main.py to connect at boot and run AP
import network
# sta_if = client interface, ap_if = ap interface
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect("accesspoint", "password")
ap_if = network.WLAN(network.AP_IF)
ap_if.active(True)
ap_if.config(authmode=3, essid="ulx3s", password="Radiona123")
print('AP config: ', ap_if.ifconfig())
print('network config:', sta_if.ifconfig())
# start uftpd by default
import uftpd
