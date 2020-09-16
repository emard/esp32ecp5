try:
  import wifiman
except:
  print("no WiFi")
import uftpd
from ntptime import settime
try:
  settime()
except:
  print("NTP not available")
