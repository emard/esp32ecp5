try:
  import wifiman
except:
  print("wifiman.py error")
import gc
gc.collect()
import uftpd
from ntptime import settime
try:
  settime()
except:
  print("NTP not available")
