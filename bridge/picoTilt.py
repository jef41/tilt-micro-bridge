''' latest change
    working on: 
                data storage management for local files - calc free spzce & size appropriately
    TODO:		
    
    tested OK:	log 'connecting to Wifi message'
    tested OK:	test if TilTHistory get_most_recent & get_averaged are returning calibration adjusted values or uncalibrated ones?
    tested OK:	csv log interval read from config file
    tested OK:	fix error (not reading most recent value) when reading most recent value
    tested OK:	ringbuffer for second Tilt is too small (configured in GF_Tilt & CSV_file)
    tested OK:	what happens with multiple Tilt colours in config for GF providers, does this work?
    tested OK:	check correct data is logged in correct locations for multiple Tilts in CSV file provider
    tested OK:	2 x Tilt 1 with name, 1 without named beer (& therefore OG), tested with CSV file handler
    not doing:	set BridgeConfig in Class attributes to avoid having to pass this refernce about
    tested OK:  add a file handler
    tested OK: 	implement wifi countrycode properly into config - test with no country code in config
    tested OK: 	adding a feature to use calibration values from config
    tested OK: 	add [[-0.001,-0.001], [10**5,10**5]] to cal points
    tested OK: 	for calibration points first 60 results printed to console only, not logged - need a better calibration process
                config.json examples for each feature, with explanation - maybe just a .md file in /examples
    tested OK: 	test with gravity or temp out of range
    tested OK: 	log info/debug uncal & cal values uploaded
    tested OK: 	separate wifi module & background checkll for wifi conenctivity
    tested OK: 	move wifi, ntp & time defs from bridge_main to lib/wifi_client module
    tested OK  	implement wifi status check/reconnect
    testing & 	possibly done?: improve non-averaging e.g. filter max, log warning if data is old, don't log if waay old
    tested OK 	modify Grainfather Tilt provider to use async update & ProviderTimer
    tested OK 	providers with different methods (averaging & latest reading)
    tested OK 	providers with different upload intervals
    tested OK: 	handle & log server responses 200, 201, 429, other - esp important if device reboots because of watchdog    
    tested OK: 	needs double check: on keyboard interrupt cancel timers & running tasks
    tested OK: 	implemented a ProviderTimer class to centralise common code - only tested with Grainfather Custom
    tested OK: 	code comments & linting
    tested OK: 	implement console & file logging for debug using logging module & io.IOBase to copy to file
    tested OK: 	de-linting
    tested OK: 	clean up some code
    tested OK: 	test & implement timers & averaging instead of rate limiter
    tested OK: 	bridge_main ble scan uses duration_ms=0 & cancel - does not consume memory
    testedOK: 	rate_limiter uses time.ticks_ms() - previously losing approx 1sec per upload, now ~400ms
    failed test: using/testing logging module - child loggers don't seem to inherit - leave this for now
    testedOK: 	test chnge to ms in rate limiter - does this improve keeping that same log minute losing 1 min/57 uploads - yup
    done: 		at startup wait averaging period before sending first data, not log period
    done: 		send a GF packet then immediately send another, how long are we asked to wait? 900 or less?
                lots of providers could cause upload time to vary, what tolerance do we have
                seem to be asked to wait 13mins 59 secs, (839 secs), not 15 mins

    todo refactor main & bridge lib to make more logical
    todo remove unnecessary libs & comments
    todo Tilt transmits at 5secs? so should no records be //5?
    todo implement watchdog (8secs max I think from memory)
    todo if reboot is because of watchdog then set upload timer to averaging period - might already be accomplished?
    todo add display - ABV latest cal SG & last averaged cal SG

    ideas:        
    button to set into calibration mode?
    
        
'''
import time # micropython-lib/python-stdlib/time extends std time module, required for strftime in debug logging
from rotating_file_handler import RotatingLogFileHandler
import logging, sys
logFormatter = logging.Formatter("%(asctime)s [%(name)-12.12s] [%(levelname)-5.5s]  %(message)s")
logger = logging.getLogger() # using no name seems necessary to log to console & file?
logger.handlers = [] # this is necessary
logger.setLevel(logging.DEBUG)

fileHandler = RotatingLogFileHandler("debug.log", (60 * 1024) - 800, 1) # kb x 1024 = bytes - 800 so we don't exceed a block boundry?
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler() #logging.StreamHandler(logging.StreamHandler(sys.stdout))
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)


from machine import Pin
import asyncio
import indicator
import bridge_main_averaging as bridge
from wifi_client import WifiClient
import gc

logger = logging.getLogger('main')
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
    await bridge.bridge_main(onboard_led, providers=None, simulate_beacons = True)# , console_log=True)


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