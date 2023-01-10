"""
python-kasa smart plug control turns on light at sunset, off at a specified time. 
Typically this code sleeps hours and wakes up twice a day to do some activity. Just like a cat!
Tested with a EP10 device.
OS tested:
  Windows 10, Ubuntu 22.04, Raspberry Pi OS 11 (bullseye) on Pi 3B+.

User supplies:
1) smart plug name (alias). Use kasa CLI to provision. This is optional but convenient.
2) lat/lon (use google map)
3) off time (24 hr, hh:mm)
4) adj min before/after sunset (+/- up to 15 min or so)

When running on Pi want to run in background at boot, probably as a cron @reboot item.

LOGIC:
On startup,
    compare local time to on/off time and today's sunset, and turn plug on/off accordingly (in case Pi reboot.) plug_state = on/off

main loop:
    if plug_state=on, calc S seconds to off time
    else, calc S seconds to on time (sunset) with any adjust
    sleep S seconds
    (awaken)
    flip plug_state state
    plug = plug_state (on/off)

Errors:
  Not much error checking, exits if plug isn't found.
  Not sure what happens during DST on/off transition. Might work ok or be off an hour that day.

Modules likely needing install:
  pip install suntime
  pip install python-kasa


------------------------ provisioning notes ---------------------------------------------
For kasa CLI commands, refer to https://python-kasa.readthedocs.io/en/latest/cli.html#provisioning

First find the plug's wifi and connect to its network, its wifi SSID ends with its 4-digit MAC.
Example: TP-LINK_Smart Plug_8714

Provision to your main router on 192.168.0.1:
>kasa --host 192.168.0.1 wifi join 'your network SSID' --password routerspasswordorhexdigits

Shorten alias name:
>kasa --alias "TP-LINK_Smart Plug_8714" alias "Plug_8714"

Test, turn on:
>kasa --alias "Plug_8714" on

"""
import platform
import asyncio
import sys
import datetime
from suntime import Sun
from kasa import (
    Discover,
    SmartPlug,
)

# provisioned already, with alias
my_alias = "Plug_8714"

# from google map
latitude = 33.0
longitude = -117.3

# timer settings
off_24time_hr = 0
off_24time_min = 5
on_adjust_minutes = -5  # turn on a few min before/after sunset, or leave at 0 if not used. Negative adjust is before sunset.


def get_sleep_until(hour: int, minute: int):
    """ get seconds until specific hour, minute (from stackoverflow)
    Args:
        hour (int): Hour
        minute (int): Minute
    """
    t = datetime.datetime.today()
    future = datetime.datetime(t.year, t.month, t.day, hour, minute)
    if t.timestamp() > future.timestamp():
        future += datetime.timedelta(days=1)
    return (future - t).total_seconds()


# returns host IP from alias, no async, from CLI code
def find_host_from_alias2(alias, target="255.255.255.255", timeout=1, attempts=3):
    """Discover a device identified by its alias."""
    for attempt in range(1, attempts):
        found_devs = asyncio.run(Discover.discover(target=target, timeout=timeout))
        for ip, dev in found_devs.items():
            if dev.alias.lower() == alias.lower():
                host = dev.host
                return host

    return None


# True=turn on plug, else turn off
async def plug_on_off(plug, pstate=False):
    if pstate:
        await plug.turn_on()
    else:
        await plug.turn_off()
    await plug.update()
    print(plug.state_information)


# call asyncio.run() once from main(), so all plug comm is in this loop, never returns.
async def plug_loop(plug):
    await plug.update()  # always update once before using

    t = datetime.datetime.today()  # now
    ss = get_sunset()
    ss += datetime.timedelta(minutes=on_adjust_minutes)
    ot = datetime.datetime(t.year, t.month, t.day, off_24time_hr, off_24time_min)  # off time
    if ss.timestamp() > ot.timestamp():
        ot += datetime.timedelta(days=1)  # off time occurs tomorrow

    # upon boot determine if plug should be on or off (initial state)
    if ss.timestamp() < t.timestamp() < ot.timestamp():
        pstate = True  # turn on if now is between sunset and off time.
    else:
        pstate = False  # turn off if now is past off time and before sunset.

    # main on/off-sleep loop
    while True:
        await plug_on_off(plug, pstate)
        if pstate:
            # calc S seconds to off time from now, to turn off
            s = get_sleep_until(off_24time_hr, off_24time_min)
            print("sleeping", s, "seconds until off")
            # upon wake up, turn off plug
            pstate = False
        else:
            # calc S seconds to sunset from now, to turn on.
            # if now is past sunset but before 00:00 then calc tomorrow's sunset.
            t = datetime.datetime.today()
            ss = get_sunset()
            ss += datetime.timedelta(minutes=on_adjust_minutes)
            if t.timestamp() > ss.timestamp():
                t += datetime.timedelta(days=1)  # on time occurs tomorrow
                ss = get_sunset(t)
                ss += datetime.timedelta(minutes=on_adjust_minutes)
            s = get_sleep_until(ss.hour, ss.minute)
            print("sleeping", s, "seconds until on")
            # upon wake up, turn on plug
            pstate = True

        await asyncio.sleep(s)


def get_sunset(date=None):
    """
    gets local sunset time with optional date.
    The default date (not time) fields returned is always yesterday...not sure why, so adjust it to today, or the specified date.
    Note: I tested this in Jan (standard time).
    """
    sun = Sun(latitude, longitude)
    today_ss = sun.get_local_sunset_time(date)
    if date is None:
        date = datetime.datetime.today()
    today_ss = datetime.datetime(date.year, date.month, date.day, today_ss.hour, today_ss.minute)  # convert to today's/specified sunset time/date
    return today_ss


if __name__ == "__main__":
    # Windows async config: https://github.com/python-kasa/python-kasa/issues/315
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    host = find_host_from_alias2(my_alias)
    if host is None:
        print("Plug ", my_alias, " not found")
        sys.exit(1)
    print(my_alias, " @ ", host)
    plug = SmartPlug(host)

    # won't return
    asyncio.run(plug_loop(plug))
