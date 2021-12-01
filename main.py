# main.py: executed on every boot
try:
  import wifiman
except:
  print('wifiman.py error')
import gc
gc.collect()
import uftpd
from ntptime import settime
try:
  settime()
  print('NTP time set')
except:
  print('NTP not available')
