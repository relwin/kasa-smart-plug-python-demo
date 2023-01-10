# kasa-smart-plug-python-demo
A short demo using python-kasa to control a smart plug.

A smart plug is programmed to turn on a light at sunset, then turn it off at a specified time.
Typically this code sleeps hours and wakes up twice a day to do some activity, just like a cat!
Tested with a EP10 device.

OS tested:
- Windows 10 (py 3.8), Ubuntu 22.04 (py 3.10), Raspberry Pi OS 11 bullseye on Pi 3B+ (py 3.9).

User supplies:
1) smart plug name (alias). Use kasa CLI to provision. This is optional but convenient.
2) lat/lon (use google map)
3) off time (24 hr, hh:mm)
4) adj min before/after sunset (+/- up to 15 min or so)

BOOTUP:
- When running on a Pi it's desired to run in the background upon bootup.
Supplied is a simple cron.d script to do this on a Pi.

LOGIC:
- On startup,
-   compare local time to on/off time and today's sunset, and turn plug on/off accordingly (in case Pi reboot.) plug_state = on/off

main loop:
- if plug_state=on, calc S seconds to off time
- else, calc S seconds to on time (sunset) with any adjust
- sleep S seconds
- (awaken)
- flip plug_state state
- plug = plug_state (on/off)
    

Errors:
- Not much error checking, exits if plug isn't found.
- Not sure what happens during DST on/off transition. Might work ok or be off an hour that day.

Modules likely needing install:
- pip install suntime
- pip install python-kasa


------------------------ provisioning notes ---------------------------------------------

For kasa CLI commands, refer to https://python-kasa.readthedocs.io/en/latest/cli.html#provisioning

First find the plug's wifi and connect to its network, its wifi SSID ends with its 4-digit MAC.
- Example: TP-LINK_Smart Plug_8714

Provision to your main router on 192.168.0.1:
>kasa --host 192.168.0.1 wifi join 'your network SSID' --password routerspasswordorhexdigits

Shorten alias name:
>kasa --alias "TP-LINK_Smart Plug_8714" alias "Plug_8714"

Test, turn on:
>kasa --alias "Plug_8714" on
