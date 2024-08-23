''' works in principle with async 
    could look at running wifi from core1 - doesn't seem to work
    look at running ble collection on core1
    investigate timestamping in tilt_status
'''
import logging
import gc
import sys
import ntptime
import network
import time
import asyncio
from aioble import central as aioble_central
#import bluetooth
#from threadsafe import ThreadSafeQueue, Message, Context
from primitives import Queue
#import _thread
from machine import RTC
from models import TiltStatus
from providers import *
from configuration import BridgeConfig
from rate_limiter import RateLimitedException

#brdg_logger = logging.getLogger("main.bridge")
#brdg_logger = logging.getLogger(__name__)
# Get a child logger of 'my_app'
logger = logging.getLogger('bridge')
logger.setLevel(logging.DEBUG)

if "RP2040" in  sys.implementation:
    import rp2
    RP2040 = True
else:
    RP2040 = False
    #network.country(country)

#############################################
# Statics
#############################################
uuid_to_colours = {
        "a495bb20-c5b1-4b44-b512-1370f02d74de": "green",
        "a495bb30-c5b1-4b44-b512-1370f02d74de": "black", 
        "a495bb10-c5b1-4b44-b512-1370f02d74de": "red",
        "a495bb60-c5b1-4b44-b512-1370f02d74de": "blue",
        "a495bb50-c5b1-4b44-b512-1370f02d74de": "orange",
        "a495bb70-c5b1-4b44-b512-1370f02d74de": "yellow",
        "a495bb40-c5b1-4b44-b512-1370f02d74de": "purple",
        "a495bb80-c5b1-4b44-b512-1370f02d74de": "pink",
        "a495bb40-c5b1-4b44-b512-1370f02d74df": "simulated"  # reserved for fake beacons during simulation mode
    }

colours_to_uuid = dict((v, k) for k, v in uuid_to_colours.items())

# Load config from file, with defaults, and args
config = BridgeConfig.load()

#reserve some space for the tilt_status object
gc.collect()
#tilt_status = bytes(0) # 80 bytes, only need 48, but cannot seem to allcoate less

#gc.threshold(2096) #4096 = memory error in BLE scan

normal_providers = [
        #PrometheusCloudProvider(config),
        #FileCloudProvider(config),
        #InfluxDbCloudProvider(config),
        #InfluxDb2CloudProvider(config),
        #BrewfatherCustomStreamCloudProvider(config),
        #BrewersFriendCustomStreamCloudProvider(config),
        GrainfatherCustomStreamCloudProvider(config),
        GrainfatherTiltStreamCloudProvider(config),
        #TaplistIOCloudProvider(config),
        #AzureIoTHubCloudProvider(config)
    ]


# Queue for holding incoming scans
#bridge_q = ThreadSafeQueue(buf=[0 for _ in range(config.queue_size + 1)])
#bridge_q = ThreadSafeQueue(buf=config.queue_size + 1)
bridge_q = Queue(maxsize=config.queue_size + 1)
scanner_running  = True
scanner_finished = False

# initiate RTC object
rtc = RTC()

# core1 line often seems to cause hangs 
#core1 = Context()  # Has an instance of _thread, so a core on RP2
#############################################
#############################################


async def bridge_main(providers, timeout_seconds: int, simulate_beacons: bool = False, console_log: bool = True):
    #logger.warning("test2")
    if providers is None:
        providers = normal_providers
    global bridge_q
    # add any webhooks defined in config
    webhook_providers = _get_webhook_providers(config)
    if webhook_providers:
        providers.extend(webhook_providers)
    # Start cloud providers
    print("Starting...")
    enabled_providers = list()
    for provider in providers:
        if provider.enabled():
            enabled_providers.append(provider)
            provider__start_message = provider.start()
            if not provider__start_message:
                provider__start_message = ''
            print("...started: {} {}".format(provider, provider__start_message))
    # Start
    if simulate_beacons: 
        scanner = asyncio.create_task(_start_beacon_simulation(bridge_q))
        print("started: simulated beacons")
    else:
        ''' start this in a thread with aioble ?
        '''
        print("starting beacon scanner...")
        scanner = asyncio.create_task(_scan_for_ibeacons()) # creates memory leak if duration_ms=0
        #pass
    try:
        a = 1200
        while True:
            # this loop will process the incoming data queue
            #handler = asyncio.create_task(_handle_bridge_queue(bridge_q, console_log))
            handler = asyncio.create_task(_handle_bridge_queue(enabled_providers, console_log))
            await handler # wait for handler to return
            if a == 1500: # getting approx 300 messages per minute so this is 5 mins
                print(f"{display_time()}\tgc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
                a = 0
            a = a + 1
            await asyncio.sleep_ms(10) # set to 0
    except KeyboardInterrupt:
        #aioble.stop()
        #scanner.stop()
        handler.cancel()
        scanner.cancel()
    except Exception as e:
        print(f"Error in bridge_main: {e}")
        raise
    #print("...started: Tilt scanner")
    
    start_time = time.time()
    end_time = start_time + timeout_seconds
    try:
        while True:
            handler = asyncio.create_task(_handle_bridge_queue(enabled_providers, console_log))
            await handler # wait for handler to return
            #print(f"gc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
            # check timeout
            if timeout_seconds:
                current_time = time.time()
                if current_time > end_time:
                    return  # stop
            await asyncio.sleep_ms(10) # testing memory leak 2000
    except KeyboardInterrupt as e:
        if not simulate_beacons:
            scanner.stop()
        print("...stopped: Tilt Scanner (keyboard interrupt)")
    except Exception as e:
        if not simulate_beacons:
            scanner.stop()
        print("...stopped: Tilt Scanner ({})".format(e))
    


#async def _start_scanner(enabled_providers: list, timeout_seconds: int, simulate_beacons: bool, console_log: bool):
async def _start_scanner(enabled_providers: list, timeout_seconds: int, simulate_beacons: bool, console_log: bool):
    if simulate_beacons:
        # Set daemon true so this thread dies when the parent process/thread dies
        #threading.Thread(name='background', target=_start_beacon_simulation, daemon=True).start()
        #scanner = asyncio.create_task(_start_beacon_simulation())
        # asyncio.create_task(_start_beacon_simulation())
        # 
        #print("starting simulated beacons")
        _thread.start_new_thread(_start_beacon_simulation, (bridge_q, ))
        print("started: simulated beacons")
    else:
        ''' start this in a thread too
            when we get to developing this with aioble
        '''
        #scanner = BeaconScanner(_beacon_callback,packet_filter=IBeaconAdvertisement)
        #scanner.start()    
        #signal.signal(signal.SIGTERM, _trigger_graceful_termination)
        #_thread.start_new_thread(scan_for_ibeacons, (bridge_q, ))
        try:
            #asyncio.run(scan_for_ibeacons(bridge_q))
            scanner = asyncio.create_task(scan_for_ibeacons()) # creates memory leak
            #pass
            # todo scanning is blocked by provider upload - makes little difference, but no data for some seconds
            #_thread.start_new_thread(scan_for_ibeacons, (bridge_q, ))
        except KeyboardInterrupt:
            aioble.stop()
        except Exception as e:
            print(f"Error: {e}")
        print("...started: Tilt scanner")
        

    print("Ready!  Listening for beacons")
    start_time = time.time()
    end_time = start_time + timeout_seconds
    try:
        while True:
            #asyncio.run(_handle_bridge_queue(enabled_providers, console_log))
            #_handle_bridge_queue(enabled_providers, console_log)
            
            handler = asyncio.create_task(_handle_bridge_queue(enabled_providers, console_log))
            #await asyncio.sleep(0) # hanlder is running
            await handler # wait for handler to return
            #print(f"gc: {gc.mem_free()}")
            # check timeout
            if timeout_seconds:
                current_time = time.time()
                if current_time > end_time:
                    print("timeout caught")
                    return  # stop
            await asyncio.sleep_ms(200) # testing memory leak 2000
    except KeyboardInterrupt as e:
        if not simulate_beacons:
            scanner.stop()
        print("...stopped: Tilt Scanner (keyboard interrupt)")
    except Exception as e:
        if not simulate_beacons:
            scanner.stop()
            print("debug: BLE scanner is finishing")
            scanner_finished = True
        print("...stopped: Tilt Scanner ({})".format(e))

async def _scan_for_ibeacons():
    ''' '''
    global bridge_q
    #print("debug: starting scanner...")
    # Constants for iBeacon
    iBeacon_prefix = b'\x4C\x00\x02\x15'  # Apple company ID + iBeacon type
    # Tilt format based on iBeacon format with Tilt specific uuid preamble (a495)
    TILT = "0215a495"
    # Start scanning for advertisements
    while True:
        async with aioble_central.scan(duration_ms=20000,
                                       interval_us=160000,
                                       window_us=16000) as scanner:
            async for result in scanner:
                # Check if the advertisement contains the iBeacon prefix
                #if result.manufacturer and result.manufacturer.startswith(IBEACON_PREFIX):
                if iBeacon_prefix in result.manufacturer():
                    # Extract and process iBeacon data
                    adv_data = result.adv_data
                    uuid = adv_data[4:20]    # UUID (16 bytes)
                    major = int.from_bytes(adv_data[20:22], 'big')  # Major (2 bytes)
                    minor = int.from_bytes(adv_data[22:24], 'big')  # Minor (2 bytes)
                    tx_power = int.from_bytes(adv_data[24:25], 'big', signed=True)  # TX Power (1 byte)
                    rssi = result.rssi
                    print(f"MAC: {result.device.addr_hex()} Beacon: {result.name}")

                    # Call the callback function with the extracted data
                    await _beacon_callback(uuid, major, minor, tx_power, rssi, bridge_q)
                    #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                else:
                    #print(f"{display_time()}\tMAC: {result.device.addr_hex()} Not beacon: {result.rssi}")
                    # fake callback
                    #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, result.rssi, bridge_q)
                    await _beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                    #pass # testing is it scanner or callback that causes issue? or maybe colours_to_uuid def?
            scanner.cancel()


async def _start_beacon_simulation(bridge_q):
    """Simulates Beacon scanning with fake events. Useful when testing or developing
    without a beacon, or on a platform with no Bluetooth support"""
    global scanner_running
    global finished
    print("...started: Tilt Beacon Simulator")
    uuid = "a495bb40-c5b1-4b44-b512-1370f02d74df" # colours_to_uuid['simulated']
    major = 70 #temp F
    minor = 1035 # gravity
    tx_power = 0
    rssi = 0
    #while True:
    while scanner_running:
        #_beacon_callback(None, None, fake_packet, dict(), bridge_q)
        _beacon_callback(uuid, major, minor, tx_power, rssi, bridge_q) 
        #time.sleep(0.1)
        #time.sleep(0.85)
        await asyncio.sleep_ms(10)
        #print("generated packet")
    print("debug: Thread is finishing")
    scanner_finished = True


#def _beacon_callback(bt_addr, rssi, packet, additional_info, bridge_q):
async def _beacon_callback(uuid, major, minor, tx_power, rssi, bridge_q):
    # todo: beacon data should be an object with attributes (including a timestamp)
    # When queue is full broadcasts should be ignored
    # this can happen because Tilt broadcasts very frequently, while Pitch must make network calls
    # to forward Tilt status info on and this can cause Pitch to fall behind
    # global cb_tilt_status
    if bridge_q.full():
        #print("debug queue is full")
        return

    colour = uuid_to_colours.get(uuid)
    if colour:
        #print("beacon_callback colour match, {}".format(colour))
        # iBeacon packets have major/minor attributes with data
        # major = degrees in F (int)
        # minor = gravity (int) - needs to be converted to float (e.g. 1035 -> 1.035)
        #start = gc.mem_free()
        beacon_data = TiltStatus(colour, major, _get_decimal_gravity(minor), config)
        #print("cb_tilt_status is:{} bytes".format(start - gc.mem_free()))
        #print("debug: tilt_status:\n{}".format(dir(tilt_status)))
        if not beacon_data.temp_valid:
            print("Ignoring broadcast due to invalid temperature: {}F".format(beacon_data.temp_fahrenheit))
        elif not beacon_data.gravity_valid:
            print("Ignoring broadcast due to invalid gravity: " + str(beacon_data.gravity))
        else:
            #print("debug: putting...\n {}".format(dir(beacon_data)))
            #bridge_q.put_nowait(beacon_data)
            #bridge_q.put_sync(beacon_data) #, block=False) # Raises IndexError if the queue is full
            try:
                await bridge_q.put(beacon_data)
            except Error as e:
                print(f"queue put error: {e}")
            #print("{}\t beacon packet received".format(beacon_data.timestamp))
            #print("debug: bridge_q after {}".format(bridge_q.qsize()))
        #print("debug: end of if colour")
    else:
        print("beacon_callback no colour match")


#def _handle_bridge_queue(enabled_providers: list, console_log: bool):
async def _handle_bridge_queue(enabled_providers: list, console_log: bool):
    #global tilt_status
    #brdg_logger.info("handle queue")
    global bridge_q
    if config.queue_empty_sleep_seconds > 0 and bridge_q.empty():
        #time.sleep(config.queue_empty_sleep_seconds)
        #print("waiting on empty queue")
        await asyncio.sleep(config.queue_empty_sleep_seconds)
        return

    if bridge_q.full(): # testing memory leak
        length = bridge_q.qsize()
        print("Queue is full ({} events), scans will be ignored until the queue is reduced".format(length))
    #start = gc.mem_free()
    #print("handle queue2")
    try:
        tilt_status = await bridge_q.get() #blocks until data available
    except IndexError:
        # Queue is empty
        print("index error queue empty")
        raise
    except Error as e:
        print(f"handler err: {e}")
        raise
    
    for provider in enabled_providers:
        try:
            start = time.time()
            #print("debug: provider:{} \n{}".format(provider, dir(tilt_status)))
            gc.collect() 
            #before_update = gc.mem_free()
            #print(f"{display_time()}\t start update")
            #print(f"processing packet with timestamp:{tilt_status.timestamp}")
            provider.update(tilt_status)
            #asyncio.create_task(provider.update(tilt_status))
            #print("update done")
            time_spent = time.time() - start
            print("{}\tUpdated provider {} for {} Tilt, took {:.3f} seconds".format(display_time(), provider, tilt_status.colour, time_spent))
            #await asyncio.sleep_ms(2000) # allow for scanning between provider updates
        except RateLimitedException:
            # nothing to worry about, just called this too many times (locally)
            pass
            #print("Skipping update due to rate limiting for provider {} for colour {}".format(provider, tilt_status.colour))
        except Exception as e:
            # todo: better logging of errors
            print("provider update error: {}".format(e))
    # Log it to console/stdout
    #print("debug SG:{} Temp:{}".format(tilt_status.gravity, tilt_status.temp_celsius))
    #print("SG:{} Temp:{}".format(tilt_status.gravity, tilt_status.temp_celsius))


def _get_decimal_gravity(gravity):
    # gravity will be an int like 1035
    # turn into decimal, like 1.035
    return gravity * .001


def _get_webhook_providers(config: PitchConfig):
    # Multiple webhooks can be fired, so create them dynamically and add to
    # all providers static list
    webhook_providers = list()
    for url in config.webhook_urls:
        webhook_providers.append(WebhookCloudProvider(url, config))
    return webhook_providers


def get_wifi(config):
    # todo this should probably loop infinitely until success
    # or maybe indicate failure
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if RP2040:
        wlan.config(pm = 0xa11140) # Disable power-save mode
        country = "GB"
        rp2.country(country)
        wlan.country(country)
    wlan.connect(config.ssid, config.password)

    # Wait for connect or fail
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        time.sleep(2)

    # Return value of cyw43_wifi_link_status
    #define CYW43_LINK_DOWN (0)
    #define CYW43_LINK_JOIN (1)
    #define CYW43_LINK_NOIP (2)
    #define CYW43_LINK_UP (3)
    #define CYW43_LINK_FAIL (-1)
    #define CYW43_LINK_NONET (-2)
    #define CYW43_LINK_BADAUTH (-3)

    # Handle connection error
    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print( 'ip = ' + status[0] )


def get_time(rtc):
    result = False
    try:
        ntptime.settime()
        print("time set to UTC:{}".format(rtc.datetime()))
        result = True
    except:
        # todo catch more specific exception
        print("npttime.settime() failed.")
    return result


def display_time():
    year, month, day, hour, mins, secs, weekday, yearday = time.localtime()
    # Print a date - YYYY-MM-DD
    return str("{:02d}:{:02d}:{:02d}".format(hour, mins, secs))



