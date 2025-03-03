''' latest change:
        WDT
    working on: 
        DONE pause on config error
        DONE check for wifi credentials
        DONE testing CSV log file auto sized seems to be overly pessimistic
        DONE testing debug.log sized from config
    TODO:
        todo refactor main & bridge lib to make more logical
        todo remove unnecessary libs & comments
        todo implement watchdog (8secs max I think from memory)
        todo if reboot is because of watchdog then set upload timer to averaging period - might already be accomplished?
        todo add display - ABV latest cal SG & last averaged cal SG

    ideas:        
    button to set into calibration mode, use different cal_config.json ?
    display
    
    __version__ = '0.1.1'    
'''
import time # micropython-lib/python-stdlib/time extends std time module, required for strftime in debug logging
#from rotating_file_handler import RotatingLogFileHandler
import logging #, sys
from logging import RotatingLogFileHandler, TimedRotatingLogFileHandler
from machine import Pin
import asyncio
import indicator
import bridge_main as bridge
from wifi_client import WifiClient
import gc

# set up root logger
logFormatter = logging.Formatter("%(asctime)s [%(name)-12.12s] [%(levelname)-5.5s]  %(message)s")
# initial log files size limit 10kb, overwritten after config loaded
#fileHandler = RotatingLogFileHandler("debug.log", (10 * 1024) - 800, 1) # kb x 1024 = bytes - 800 so we don't exceed a block boundry?
log_max_kb = bridge.config.debug_log[0] if bridge.config else 10
log_nbr_backups = bridge.config.debug_log[1] if bridge.config else 1
#fileHandler = RotatingLogFileHandler("debug.log", (log_max_kb * 1024), log_nbr_backups)
fileHandler = TimedRotatingLogFileHandler("debug.log", (log_max_kb * 1024), log_nbr_backups, write_secs=300)
fileHandler.setFormatter(logFormatter)
consoleHandler = logging.StreamHandler() #logging.StreamHandler(logging.StreamHandler(sys.stdout))
consoleHandler.setFormatter(logFormatter)

logger = logging.getLogger() # using no name seems necessary to log to console & file?
logger.handlers = [] # this is necessary
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.INFO)
logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)

#logger = logging.getLogger('main')
logger = logging.getLogger()
logger.info("***  Startup")
gc.collect()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())


def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)


async def main():
    set_global_exception()  # Debug aid
    #await bridge.bridge_main(providers=None, timeout_seconds=0, simulate_beacons = False, console_log=True)
    global onboard_led # = indicator.Status() # turn on the LED status indicator
    #await bridge.bridge_main(onboard_led, providers=None, simulate_beacons=False)# , console_log=True)
    await bridge.bridge_main(onboard_led, providers=bridge_providers, simulate_beacons=True)


async def hold_up():
    while True:
        await asyncio.sleep(8)
        # feed wdt
        if bridge.wdt:
            bridge.wdt.feed()


onboard_led = indicator.Status() # turn on the LED status indicator

if bridge.initialise():
    # re-assign max log size from config
    log_max_kb = bridge.config.debug_log[0] if bridge.config else 10
    log_nbr_backups = bridge.config.debug_log[1] if bridge.config else 1
    logger.handlers[0].max_file_size_in_bytes = log_max_kb * 1024
    logger.handlers[0].number_of_backup_files = log_nbr_backups
    # test if wifi creds included, 
    wifi = WifiClient(bridge.config)
    bridge_providers = bridge.get_providers(wifi.has_config)

else:
    # hold here, cannot proceed, error with config.json
    asyncio.run(hold_up())

# enter main loop
try:
    asyncio.run(main())
except KeyboardInterrupt as e:
    for provider in bridge.provider_timers.timer_list.keys():
        bridge.provider_timers.stop(provider)
    #bridge.handler.cancel()
    #await asyncio.sleep(0)
    #bridge.scanner.cancel()
    #await asyncio.sleep(0)
    print("...stopped: Tilt Scanner (keyboard interrupt)")
except Exception as e:
    for provider in bridge.provider_timers.timer_list.keys():
        bridge.provider_timers.stop(provider)
    print("...stopped: Tilt Scanner ({})".format(e))
finally:
    asyncio.new_event_loop()  # Clear retained state
    Pin('LED',Pin.OUT).off()
