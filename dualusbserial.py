# MicroPython >= 1.25 USB dual serial port example
#
# LICENSE=BSD AUTHOR=EMARD
#
# Example demonstrating primary serial port as micropython prompt
# and secondary serial port as usb-serial passthru
# on a dynamic CDCInterface() serial port.
#
# To run this example:
#
# 1. Install "usb-device-cdc": mpremote mip install usb-device-cdc
#
# 2. Run the example via: mpremote run --no-follow dualusbserial.py
#
# 3. mpremote needs --no-follow to avoid exit with an error, because when the
#    example runs the existing USB device disconnects and then re-enumerates with
#    the second serial port. If you check (for example by running mpremote connect
#    list) then you should now see two USB serial devices.
#
# 4. This example will not work if started from USB serial REPL like:
#    >>> import dualusbserial.py
#
# 5. Connect to one of the new ports: mpremote connect PORTNAME
#
#    It may be necessary to type Ctrl-B to exit the raw REPL mode and resume the
#    interactive REPL after mpremote connects.

import os
import time
import usb.device
from usb.device.cdc import CDCInterface
from machine import UART
import select
import asyncio

async def read_write(rd, wr):
  while True:
    # the await keyword gives control back to eventloop
    # and will block here, until control is given back
    # also telling uart how much data to read
    # stream.s is the UART instance
    # on network, it's a socket
    #uart.write(await stream.read())
    #cdc.write(await stream.read())
    wr.write(await rd.read(256))

async def main():
  # create UART TTL serial
  # pins tx=43, rx=44 are boot default for REPL (python prompt) on UART0
  # it is recommended to use other pins
  uart = UART(2, tx=1, rx=2, baudrate=115200)

  # create USB serial
  cdc = CDCInterface()
  cdc.init(timeout=0)  # zero timeout makes this non-blocking, suitable for os.dupterm()

  # pass builtin_driver=True so that we get the built-in USB-CDC alongside,
  # if it's available.
  usb.device.get().init(cdc, builtin_driver=True)

  print("Waiting for USB host to configure the interface...")

  # wait for host enumerate as a CDC device...
  while not cdc.is_open():
    time.sleep_ms(100)

  read_uart  = asyncio.StreamReader(uart)
  read_usb   = asyncio.StreamReader(cdc)
  write_uart = asyncio.StreamWriter(uart)
  write_usb  = asyncio.StreamWriter(cdc)
  # await read(read_uart) or read(read_usb) # would block forever, because in read is a while True loop
  asyncio.create_task(read_write(read_uart, write_usb)) # does not block, the eventloop has the control over the task
  asyncio.create_task(read_write(read_usb, write_uart)) # does not block, the eventloop has the control over the task
  # if await is used in front of asyncio.create_task, then you'll get the return value, but a while True loop never finishes
  # this will also block until the task is finished
  print("Receiving for 30 seconds")
  await asyncio.sleep(30) # blocks for 30 seconds
  # async main is left here and all remaining tasks should be removed

if __name__ == "__main__":
    asyncio.run(main())
