# ecp5.py for new pinout

This is new pinout for v3.1.4 and future ULX3S boards.
It uses different JTAG pinout to free fixed
pins reserved for RMII Ethernet adater.

The ecp5.py code is different because
the new pinout doesn't have some TCK glitches
which old pinout had.

I'm not sure is it really glitch-free now but at
least glitches don't need workaround at flash
code.
