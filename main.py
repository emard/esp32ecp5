try:
  import wifiman
except:
  print("no wifiman.py")
import gc
gc.collect()
import uftpd
from ntptime import settime
try:
  settime()
except:
  print("NTP not available")
