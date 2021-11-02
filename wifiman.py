import network
import time

def read_profiles():
  with open("wifiman.conf") as f:
    lines = f.readlines()
  profiles = {}
  for line in lines:
    if line.find(":")>=0:
      ssid, password = line.strip("\n").split(":")
      profiles[ssid] = password
  return profiles

wlan_sta = network.WLAN(network.STA_IF)

def get_connection():
  """return a working WLAN(STA_IF) instance or None"""

  # First check if there already is any connection:
  if wlan_sta.isconnected():
    return wlan_sta

  connected = False
  try:
    # ESP connecting to WiFi takes time, wait a bit and try again:
    time.sleep(3)
    if wlan_sta.isconnected():
        return wlan_sta

    # Read known network profiles from file
    profiles = read_profiles()

    # Search WiFis in range
    wlan_sta.active(True)
    networks = wlan_sta.scan()

    AUTHMODE = {0: "open", 1: "WEP", 2: "WPA-PSK", 3: "WPA2-PSK", 4: "WPA/WPA2-PSK"}
    for ssid, bssid, channel, rssi, authmode, hidden in sorted(networks, key=lambda x: x[3], reverse=True):
      ssid = ssid.decode('utf-8')
      encrypted = authmode > 0
      print("ssid: %s chan: %d rssi: %d authmode: %s" % (ssid, channel, rssi, AUTHMODE.get(authmode, '?')))
      if encrypted:
        if ssid in profiles:
          password = profiles[ssid]
          connected = do_connect(ssid, password)
      else:  # open
        connected = do_connect(ssid, None)
      if connected:
        break

  except OSError as e:
    print("exception", str(e))

  return wlan_sta

def do_connect(ssid, password):
  wlan_sta.active(True)
  if wlan_sta.isconnected():
    return None
  wlan_sta.connect(ssid, password)
  for retry in range(100):
    connected = wlan_sta.isconnected()
    if connected:
      break
    time.sleep(0.1)
  return connected

get_connection()
