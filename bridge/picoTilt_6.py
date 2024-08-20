''' integrate aioble scanner into thread on core1
    
    todo if this works maybe queue should include a timestamp?
    
    todo in bridge_main _handle_pitch_queue could also hold a circular buffer
    for each configured tilt
    maybe hold last 60 values? then provide an averaged/normalised result
    
    button to set into calibration mode?
    
    method to idetnify a starting gravity & then calc ABV etc.
    
    for GF priovider, if response is 429 then (re)set timer to 1 minute, if 201 then timer to 15 mins?
    at present after a 429 will wait 15 mins before retry
    
    todo remove unnecessary libs & comments
    todo fork tilt_Pitch & put on github
    
    todo implement aioble to return SG & temp & uuid & timestamp to queue
    todo implement watchdog (8secs max I think from memory)import ussl
    todo implement wifi countrycode properly into config
    todo implement wifi status check/reconnect
    
    async5 is an attempt to allow scanning between providers - 2secs of async await
    
'''

#from bridge_main import *
#from bridge_main_asyncv3 import *
#import bridge_main_asyncv4 as bridge
#import bridge_main_asyncv5 as bridge
import bridge_main_asyncv6 as bridge
import asyncio
import _thread
import time
import gc

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
    await bridge.bridge_main(providers=None, timeout_seconds=0, simulate_beacons = False, console_log=True)
    #await bridge.bridge_main(providers=None, timeout_seconds=0, simulate_beacons = True, console_log=True)

    
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


