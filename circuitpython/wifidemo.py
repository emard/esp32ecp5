import wifi

for net in wifi.radio.start_scanning_networks():
  print(net.ssid)
wifi.radio.stop_scanning_networks()
wifi.radio.connect("user","password")
print(wifi.radio.ipv4_address)

import ipaddress
print(wifi.radio.ping(ipaddress.ip_address("192.168.48.254")))
