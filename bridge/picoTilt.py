''' 
    changes in this version:
    implement console & file logging for debug using logging module & io.IOBase to copy to file
    de-linting
    
    tested OK: clean up some code
    tested OK: test & implement timers & averaging instead of rate limiter
    tested OK: bridge_main ble scan uses duration_ms=0 & cancel - does not consume memory
    testedOK: rate_limiter uses time.ticks_ms() - previously losing approx 1sec per upload, now ~400ms
    failed test: using/testing logging module - child loggers don't seem to inherit - leave this for now
    testedOK: test chnge to ms in rate limiter - does this improve keeping that same log minute losing 1 min/57 uploads - yup
    
    todo on keyboard interrupt cancel timers & running tasks
    todo move wifi, ntp & time defs from bridge_main to net-utility module
    todo handle & log server responses 200, 201, 429, other - esp important if device reboots because of watchdog
    todo at startup wait averaging period before sending first data, not log period
    todo refactor main & bridge lib to make more logical
    todo remove unnecessary libs & comments
    todo Tilt transmits at 5secs? so should no records be //5?
    todo improve non-averaging e.g. filter max
    todo make provider.uploads task(s)
    todo implement aioble to return SG & temp & uuid & timestamp to queue
    todo implement watchdog (8secs max I think from memory)import ussl
    todo implement wifi countrycode properly into config
    todo implement wifi status check/reconnect
    todo send a GF packet then immediately send another, how long are we asked to wait? 900 or less? lots of providers could cause upload time to vary, what tolerance do we have
    
    ideas:
    integrate aioble scanner into thread on core1
        
    button to set into calibration mode?
    
    method to identify a starting gravity & then calc ABV etc.
        
'''

import time # micropython-lib/python-stdlib/time extends std time module, required for strftime in debug logging
import logging, sys, os, io


def get_log_file():
    for i in range(10):
        fn = "debug_" + str(i) + ".log"
        try:
            f = open(fn, "r")
            # continue with the file.
        except OSError:  # open failed
           fn = "debug_0.log" if i == 10 else fn
           break
    return fn

log_file = get_log_file()

class logToFile(io.IOBase):
    def __init__(self):
        pass
 
    def write(self, data):
        with open(log_file, mode="a+") as f:
            f.write(data)
        return len(data)


logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s]:%(name)s:\t%(message)s")

my_logger = logging.getLogger('main')  # Parent logger
 
# now your console text output is saved into file
os.dupterm(logToFile())
# todo this will munch up storage space; really want ot limit log file to 150KB & also rotate log files


#import bridge_main_asyncv5 as bridge
import bridge_main_averaging as bridge
import asyncio
#import _thread
import gc
'''
# Create a logger specifically for the main module
root_logger = logging.getLogger()  # Parent logger

# Configure the logger
root_logger.setLevel(logging.DEBUG)  # Set the logging level for other modules

# Create a console handler and set the format
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s: %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Create a file handler and set the format
file_handler = logging.FileHandler('app.log', mode='w')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s: %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
# Add handlers to the root logger
#logging.getLogger().addHandler(console_handler)
#logging.getLogger().addHandler(file_handler)

# set root logger
#logging.basicConfig(level=logging.DEBUG)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("%(asctime)s: %(name)s - %(levelname)s - %(message)s"))
 
logger = logging.getLogger('main')
logger.setLevel(logging.DEBUG) # level for this module
# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# test message
logger.info("test1")
'''
logger = logging.getLogger('main')
logger.info("Startup")
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
    await bridge.bridge_main(providers=None, timeout_seconds=0, simulate_beacons = True, console_log=True)

    
# get wifi network
bridge.get_wifi(bridge.config)

# set system time - could have a UTC offset in config, but time is onyl used internally at the moment
bridge.get_time(bridge.rtc)

# enter main loop
try:
    asyncio.run(main())
except KeyboardInterrupt as e:
    #if not simulate_beacons:
    #    scanner.stop()
    #_thread.exit()
    bridge.scanner_running = False
    while not bridge.scanner_finished:
        asyncio.sleep_ms(100)
    os.dupterm(None)
    print("Thread reports finished")
    print("...stopped: Tilt Scanner (keyboard interrupt)")
except Exception as e:
    #if not bridge.simulate_beacons:
    #bridge.scanner.stop()
    #_thread.exit()
    #bridge.handler.cancel()
    #bridge.scanner.cancel()
    os.dupterm(None)
    print("...stopped: Tilt Scanner ({})".format(e))
finally:
    asyncio.new_event_loop()  # Clear retained state


