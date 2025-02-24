''' latest change
                redesign simulated beacon generation
                testing CSV log file auto sized seems to be overly pessimistic
                testing debug.log sized from config
    working on: 
                
    TODO:		
    
    todo refactor main & bridge lib to make more logical
    todo remove unnecessary libs & comments
    todo Tilt transmits at 5secs? so should no records be //5?
    todo implement watchdog (8secs max I think from memory)
    todo if reboot is because of watchdog then set upload timer to averaging period - might already be accomplished?
    todo add display - ABV latest cal SG & last averaged cal SG

    ideas:        
    button to set into calibration mode, use different cal_config.json ?
    display
    
        
'''
import time # micropython-lib/python-stdlib/time extends std time module, required for strftime in debug logging
#from rotating_file_handler import RotatingLogFileHandler
import logging #, sys
from logging import RotatingLogFileHandler, TimedRotatingLogFileHandler
from machine import Pin
import asyncio
import indicator
import bridge_main_averaging as bridge
from wifi_client import WifiClient
import gc

# set up root logger
logFormatter = logging.Formatter("%(asctime)s [%(name)-12.12s] [%(levelname)-5.5s]  %(message)s")
# initial log files size limit 10kb, overwritten after config loaded
#fileHandler = RotatingLogFileHandler("debug.log", (10 * 1024) - 800, 1) # kb x 1024 = bytes - 800 so we don't exceed a block boundry?
log_max_kb = bridge.config.debug_log[0]
log_nbr_backups = bridge.config.debug_log[1]
#fileHandler = RotatingLogFileHandler("debug.log", (log_max_kb * 1024), log_nbr_backups)
fileHandler = TimedRotatingLogFileHandler("debug.log", (log_max_kb * 1024), log_nbr_backups, write_secs=300)
fileHandler.setFormatter(logFormatter)
consoleHandler = logging.StreamHandler() #logging.StreamHandler(logging.StreamHandler(sys.stdout))
consoleHandler.setFormatter(logFormatter)

logger = logging.getLogger() # using no name seems necessary to log to console & file?
logger.handlers = [] # this is necessary
logger.setLevel(logging.DEBUG)
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
    await bridge.bridge_main(onboard_led, providers=None, simulate_beacons=True)


onboard_led = indicator.Status() # turn on the LED status indicator    
# get wifi network
#bridge.get_wifi(bridge.config)
wifi = WifiClient(bridge.config)
asyncio.run(wifi.connect(onboard_led))

# set system time - could have a UTC offset in config, but time is onyl used internally at the moment
bridge.get_time(bridge.rtc)

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