import cppmem
# Switch C++ memory allocations to use MicroPython's heap
cppmem.set_mode(cppmem.MICROPYTHON)

import os
# create a local /main.py if it does not exist
try:
    os.stat('/main.py')
except OSError:
    with open("/main.py", "w") as f:
        f.write("""\
import time  # micropython-lib/python-stdlib/time extends std time module, required for strftime in debug logging
import logging
from logging import TimedRotatingLogFileHandler
from machine import Pin
import asyncio
import indicator
from bridge_main import BridgeMain
from wifi_client import WifiClient
import gc
gc.collect()
# DEBUG_LEVEL = logging.DEBUG
# SIMULATE_BEACONS = True
DEBUG_LEVEL = logging.INFO
SIMULATE_BEACONS = False


def set_global_exception():
    def handle_exception(loop, context):
        import sys

        sys.print_exception(context["exception"])
        sys.exit()

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


async def main():
    set_global_exception()  # Debug aid
    global onboard_led  # = indicator.Status() # turn on the LED status indicator
    await bridge.bridge_main(onboard_led, simulate_beacons=SIMULATE_BEACONS)
    # await bridge.bridge_main(onboard_led, providers=bridge_providers, simulate_beacons=True)


async def hold_up():
    while True:
        await asyncio.sleep(8)
        # feed wdt
        if bridge.wdt:
            bridge.wdt.feed()


# set up root logger
logFormatter = logging.Formatter(
    "%(asctime)s [%(name)-12.12s] [%(levelname)-5.5s]  %(message)s"
)
# initial log files size limit 10kb, overwritten after config loaded
log_max_kb = 12
log_nbr_backups = 1
fileHandler = TimedRotatingLogFileHandler(
    "debug.log", (log_max_kb * 1024), log_nbr_backups, write_secs=300
)
fileHandler.setFormatter(logFormatter)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)

logger = logging.getLogger()  # root logger
logger.handlers = []  # this is necessary
logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)
logger.setLevel(DEBUG_LEVEL)

logger.info("***  Startup")
gc.collect()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

onboard_led = indicator.Status()  # turn on the LED status indicator
onboard_led.on()
bridge = BridgeMain()

if bridge.initialised():
    # re-assign max log size from config
    log_max_kb = bridge.config.debug_log[0] if bridge.config else 10
    log_nbr_backups = bridge.config.debug_log[1] if bridge.config else 1
    logger.handlers[0].max_file_size_in_bytes = log_max_kb * 1024
    logger.handlers[0].number_of_backup_files = log_nbr_backups
    
    if bridge.display:
        bridge.display.show_msg("config file loaded")
    # test if wifi creds included,
    wifi = WifiClient(bridge.config)
    if wifi.has_config:
        if bridge.display:
            bridge.display.show_msg("connecting to wifi...")
        asyncio.run(wifi.connect(onboard_led, bridge.display))

        if bridge.display:
            bridge.display.show_msg("wifi connected \\nget NTP time")
        # set system time - could have a UTC offset in config, but time is only used internally at the moment
        bridge.get_time()
    # provision the providers referenced in config.json, called here so the wifi referrnce doesn't have to be passed around
    bridge.set_providers(wifi.has_config)

    if bridge.display:
        bridge.display.show_msg("startup complete")
    
    # enter main loop
    try:
        asyncio.run(main())
    except KeyboardInterrupt as e:
        for provider in bridge.provider_timers.timer_list.keys():
            bridge.provider_timers.stop(provider)
        print("...stopped: Tilt Scanner (keyboard interrupt)")   
        if bridge.display:
            #if bridge.display_updater:
            bridge.display_updater.cancel()
            bridge.display.lcd.clear()
            bridge.display.lcd.set_backlight(0)
        if bridge.rgb_led:
            bridge.rgb_led.off()
    except Exception as e:
        for provider in bridge.provider_timers.timer_list.keys():
            bridge.provider_timers.stop(provider)
        print(f"...stopped: Tilt Scanner ({e})")
        if bridge.display:
            bridge.display_updater.cancel()
            bridge.display.lcd.clear()
            bridge.display.lcd.set_backlight(0)
        if bridge.rgb_led:
            bridge.rgb_led.off()
        raise
    finally:
        asyncio.new_event_loop()  # Clear retained state
        onboard_led.off()
else:
    # hold here, cannot proceed, error with config.json
    onboard_led.on()

__version__ = "1.1.2"

""")

# todo we could create a basic config.json here?
try:
    os.stat('/config.json')
except OSError:
    with open("/config.json", "w") as f:
        f.write("""\
{
    enter your config here
}
""")