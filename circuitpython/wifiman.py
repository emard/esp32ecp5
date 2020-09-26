import wifi,time

def read_profiles():
  with open("wifiman.conf") as f:
    lines = f.readlines()
  profiles = {}
  for line in lines:
    ssid, password = line.strip("\n").split(":")
    profiles[ssid] = password
  return profiles

# TODO retry connection 100x
def do_connect(ssid, password):
  if wifi.radio.ipv4_address:
    return True
  wifi.radio.connect(ssid,password)
  if wifi.radio.ipv4_address:
    return True
  return False

def get_connection():
  """return a working WLAN(STA_IF) instance or None"""

  # First check if there already is any connection:
  if(wifi.radio.ipv4_address):
    return

  connected = False
  try:
    # ESP connecting to WiFi takes time, wait a bit and try again:
    time.sleep(3)
    if(wifi.radio.ipv4_address):
      return

    # Read known network profiles from file
    profiles = read_profiles()

    # Search WiFis in range
    networks = []
    for net in wifi.radio.start_scanning_networks():
      networks.append(net)
    wifi.radio.stop_scanning_networks()

    # sort from strongest to weakest
    for net in sorted(networks, key=lambda x: x.rssi, reverse=True):
      if net.ssid in profiles:
        print("trying",net.ssid)
        password = profiles[net.ssid]
        connected = do_connect(net.ssid, password)
      if connected:
        break

  except OSError as e:
    print("exception", str(e))

  return

get_connection()
print(wifi.radio.ipv4_address)
