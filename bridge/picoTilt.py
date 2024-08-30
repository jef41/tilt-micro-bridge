''' 
    changes in this version:
    clean up some code
    test & implement averaging    
        
    tested OK: bridge_main ble scan uses duration_ms=0 & cancel - does not consume memory
    testedOK: rate_limiter uses time.ticks_ms() - previously losing approx 1sec per upload, now ~400ms
    failed test: using/testing logging module - child loggers don't seem to inherit - leave this for now
    
    todo handle & log server responses 200, 201, 429, other
    todo implement console & file logging for debug
    todo remove unnecessary libs & comments
    todo move wifi, ntp & time defs from bridge_main to net-utility module
    todo make provider.uploads tasks
    todo test chnge to ms in rate limiter - does this improve keeping that same log minute losing 1 min/57 uploads
    todo implement aioble to return SG & temp & uuid & timestamp to queue
    todo implement watchdog (8secs max I think from memory)import ussl
    todo implement wifi countrycode properly into config
    todo implement wifi status check/reconnect
    todo send a GF packet then immediately send another, how long are we asked to wait? 900 or less?
    
    ideas:
    integrate aioble scanner into thread on core1
    
    todo if this works maybe queue should include a timestamp?
    
    todo in bridge_main _handle_pitch_queue could also hold a circular buffer
    for each configured tilt
    maybe hold last 60 values? then provide an averaged/normalised result
    
    button to set into calibration mode?
    
    method to idetnify a starting gravity & then calc ABV etc.
    
    for GF priovider, if response is 429 then (re)set timer to 1 minute, if 201 then timer to 15 mins?
    at present after a 429 will wait 15 mins before retry
    
'''

import time # micropython-lib/python-stdlib/time extends std time module, required for strftime in debug logging
#import logging #, sys
#from bridge_main import *
#from bridge_main_asyncv3 import *
#import bridge_main_asyncv4 as bridge
#import bridge_main_asyncv5 as bridge
import bridge_main_averaging as bridge
import asyncio
import _thread
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
    print("Thread reports finished")
    print("...stopped: Tilt Scanner (keyboard interrupt)")
except Exception as e:
    #if not bridge.simulate_beacons:
    #bridge.scanner.stop()
    #_thread.exit()
    #bridge.handler.cancel()
    #bridge.scanner.cancel()
    print("...stopped: Tilt Scanner ({})".format(e))
finally:
    asyncio.new_event_loop()  # Clear retained state


