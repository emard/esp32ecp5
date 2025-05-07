[ ] autmount /sd
[ ] ESP32-S2 sdraw.py support
[ ] try printing stdio lines in real time
[ ] setup could ask to remove old files from root
[ ] watchdog in uftpd
[ ] freeze after 5-10 times site ecp5.prog(\"passthru21111043.bit.gz\")
[ ] micropython 1.21 zlib
[ ] mip.install("https://raw.githubusercontent.com/emard/esp32ecp5/master")
[ ] ptp.py flash_addr must increment on even address
    in the first packet read 12 byte of PTP header and then the
    rest should be received as even addresses
[ ] ptp.py 4096 byte even buffering for flash
    from micropython import RingIO
    rio=RingIO(4097) # for 4096 it needs 1 extra
    rio.write(b"1234") # many ...
    rio.read(4096)
