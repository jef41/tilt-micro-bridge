''' 
    testing: handle & log server responses 200, 201, 429, other - esp important if device reboots because of watchdog    
    
    tested OK: needs double check: on keyboard interrupt cancel timers & running tasks
    tested OK: implemented a ProviderTimer class to centralise common code - only tested with Grainfather Custom
    tested OK: code comments & linting
    tested OK: implement console & file logging for debug using logging module & io.IOBase to copy to file
    tested OK: de-linting
    tested OK: clean up some code
    tested OK: test & implement timers & averaging instead of rate limiter
    tested OK: bridge_main ble scan uses duration_ms=0 & cancel - does not consume memory
    testedOK: rate_limiter uses time.ticks_ms() - previously losing approx 1sec per upload, now ~400ms
    failed test: using/testing logging module - child loggers don't seem to inherit - leave this for now
    testedOK: test chnge to ms in rate limiter - does this improve keeping that same log minute losing 1 min/57 uploads - yup
    done: at startup wait averaging period before sending first data, not log period
    done: send a GF packet then immediately send another, how long are we asked to wait? 900 or less? lots of providers could cause upload time to vary, what tolerance do we have
            seem to be asled to wait 13mins 59 secs, or maybe 14 mins (839 secs)

    todo modify Grainfather Tilt provider to use async update & ProviderTimer
    todo move wifi, ntp & time defs from bridge_main to net-utility module
    todo refactor main & bridge lib to make more logical
    todo remove unnecessary libs & comments
    todo Tilt transmits at 5secs? so should no records be //5?
    todo improve non-averaging e.g. filter max, log warning if data is old, don't log if waay old
    todo implement watchdog (8secs max I think from memory)import ussl
    todo implement wifi countrycode properly into config
    todo implement wifi status check/reconnect
    todo if reboot is because of watchdog then set upload timer to averaging period - might already be accomplished?

    ideas:
    integrate aioble scanner into thread on core1
        
    button to set into calibration mode?
    
    method to identify a starting gravity & then calc ABV etc.
        
'''

import time # micropython-lib/python-stdlib/time extends std time module, required for strftime in debug logging
from rotating_file_handler import RotatingLogFileHandler
import logging, sys
logFormatter = logging.Formatter("%(asctime)s [%(name)-12.12s] [%(levelname)-5.5s]  %(message)s")
logger = logging.getLogger()
logger.handlers = [] # this is necessary
logger.setLevel(logging.DEBUG)

fileHandler = RotatingLogFileHandler("debug.log", 100_000, 8) #logging.FileHandler("duallog.txt")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler() #logging.StreamHandler(logging.StreamHandler(sys.stdout))
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


#import bridge_main_asyncv5 as bridge
import bridge_main_averaging as bridge
import asyncio
#import _thread
import gc

logger = logging.getLogger('main')
logger.info("**************  Startup")
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
    await bridge.bridge_main(providers=None, timeout_seconds=0, simulate_beacons = True)# , console_log=True)

    
# get wifi network
bridge.get_wifi(bridge.config)

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