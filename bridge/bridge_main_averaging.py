''' works in principle with async 
    could look at running wifi from core1 - doesn't seem to work
    look at running ble collection on core1
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
from models import TiltStatus, TiltHistory
from providers import *
from configuration import BridgeConfig
#from rate_limiter import RateLimitedException
from models.provider_timer import UploadTimers

#brdg_logger = logging.getLogger("main.bridge")
#brdg_logger = logging.getLogger(__name__)
# Get a child logger of 'my_app'
logger = logging.getLogger('bridge')
#logger.setLevel(logging.DEBUG)

if "RP2040" in  sys.implementation._machine:
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
# Queue for holding incoming scans
#bridge_q = Queue(1) # Queue(maxsize=config.queue_size + 1)
data_archive = bytearray()
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


provider_timers = UploadTimers()
handler = None
scanner = None
#scanner_running  = True
#scanner_finished = False

# initiate RTC object
rtc = RTC()

# core1 line often seems to cause hangs 
#core1 = Context()  # Has an instance of _thread, so a core on RP2
#############################################
#############################################


async def bridge_main(providers, timeout_seconds: int, simulate_beacons: bool = False):
    # todo don't think we need timeout_seconds any longer? check
    # todo remove providers here too?
    global data_archive
    global provider_timers
    global handler
    global scanner
    if providers is None:
        providers = normal_providers
    # add any webhooks defined in config
    # !! not currently implemented/tested
    webhook_providers = _get_webhook_providers(config)
    if webhook_providers:
        providers.extend(webhook_providers)
    # Start cloud providers
    logger.info("Starting...")
    enabled_providers = list()
    enabled_colours = list()
    for provider in providers:
        if provider.enabled():
            enabled_providers.append(provider)
            provider__start_message = provider.start() #todo look into this
            if not provider__start_message:
                provider__start_message = ''
            logger.info("...started: {} {}".format(provider, provider__start_message))
            #todo: find configured colours, then initiate the TiltHistory object
            #.colour_urls.keys()
            for colour in provider.colour_urls.keys():
                if colour not in enabled_colours:
                    enabled_colours.append(colour) 
    gc.collect()
    
    # replace config with max_of_averaging, pass a dict of colour:max_av
    # data_archive = TiltHistory(config, colour_dict())
    #data_archive = TiltHistory(config, enabled_colours)
    #data_archive = TiltHistory(config, colour_dict(enabled_providers, enabled_colours))
    data_archive = TiltHistory(colour_dict(enabled_providers, enabled_colours))
    for provider in enabled_providers:
        provider.attach_archive(data_archive)
        provider_timers.add(provider, provider.period, provider.averaging_period)
    # Start
    if simulate_beacons: 
        #scanner = asyncio.create_task(_start_beacon_simulation(bridge_q))
        scanner = asyncio.create_task(_scan_for_ibeacons(simulate=True)) 
        logger.info("started: simulated beacons")
    else:
        ''' start this in a thread with aioble ?
        '''
        logger.info("starting beacon scanner...")
        scanner = asyncio.create_task(_scan_for_ibeacons()) 
        #pass
    try:
        a = 1200 # for debugging
        while True:
            # this loop will process the incoming data queue
            #handler = asyncio.create_task(_handle_bridge_queue(bridge_q, console_log))
            handler = asyncio.create_task(_handle_bridge_queue(enabled_providers)) #, console_log))
            await handler # wait for handler to return
            if a == 1500: # getting approx 300 messages per minute so this is 5 mins
                logger.debug(f"gc: {gc.mem_free()}")#\t qsize:{bridge_q.qsize()}")
                a = 0
            a = a + 1 # for debugging
            await asyncio.sleep_ms(10) # was set to 10
    except asyncio.CancelledError:
        print('Trapped cancelled error.')
        raise
    except KeyboardInterrupt:
        #aioble.stop()
        #scanner.stop()
        handler.cancel()
        scanner.cancel()
    except Exception as e:
        logger.info(f"Error in bridge_main: {e}")
        raise
    #logger.info("...started: Tilt scanner")
    # todo below this line isn't doing anything? check
    try:
        while True:
            handler = asyncio.create_task(_handle_bridge_queue(enabled_providers)) #, console_log))
            await handler # wait for handler to return
            #logger.debug(f"gc: {gc.mem_free()}\t qsize:{bridge_q.qsize()}")
            # check timeout
            if timeout_seconds:
                current_time = time.time()
                if current_time > end_time:
                    return  # stop
            await asyncio.sleep_ms(10) 
    except KeyboardInterrupt as e:
        #if not simulate_beacons:
        scanner.stop()
        logger.info("...stopped: Tilt Scanner (keyboard interrupt)")
    except Exception as e:
        #if not simulate_beacons:
        scanner.stop()
        logger.info("...stopped: Tilt Scanner ({})".format(e))


async def _scan_for_ibeacons(simulate=False):
    ''' '''
    #global bridge_q
    #logger.info("debug: starting scanner...")
    # Constants for iBeacon
    iBeacon_prefix = b'\x4C\x00\x02\x15'  # Apple company ID + iBeacon type
    # Tilt format based on iBeacon format with Tilt specific uuid preamble (a495)
    TILT = "0215a495"
    # Start scanning for advertisements
    while True:
        async with aioble_central.scan(duration_ms=1000, 
                                       interval_us=160000,
                                       window_us=16000) as scanner:
            try:
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
                        logger.info(f"MAC: {result.device.addr_hex()} Beacon: {result.name}")

                        # Call the callback function with the extracted data
                        await _beacon_callback(uuid, major, minor, tx_power, rssi)#, bridge_q)
                        #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                    if simulate:
                        #logger.info(f"MAC: {result.device.addr_hex()} Not beacon: {result.rssi}")
                        # fake callback
                        import random
                        uuid = random.choice(list(uuid_to_colours.keys()))
                        major = random.randrange(500, 850) # HD ->SD (50, 85)
                        minor = random.randrange(10050, 10450) # HD -> SD (1005, 1045)
                        await _beacon_callback(uuid, major, minor, 0, 0)#, bridge_q)
                        #pass # testing is it scanner or callback that causes issue? or maybe colours_to_uuid def?
            except AttributeError:
                #logger.info(f"scanner result is:{result} scanner is:{scanner}")
                #logger.info(f"scanner result.adv_data is {result.adv_data}")
                logger.info(f"Attribute Error")
                #raise
        asyncio.sleep_ms(100)


#def _beacon_callback(bt_addr, rssi, packet, additional_info, bridge_q):
async def _beacon_callback(uuid, major, minor, tx_power, rssi):#, bridge_q):
    global data_archive
    # todo: this isn't actually an async routine
    # check bluetooth data and store on a queue (TiltHistory object)
    #    return

    colour = uuid_to_colours.get(uuid)
    if colour in data_archive.ringbuffer_list:
        #logger.info("beacon_callback colour match, {}".format(colour))
        # iBeacon packets have major/minor attributes with data
        # major = degrees in F (int)
        # minor = gravity (int) - needs to be converted to float (e.g. 1035 -> 1.035)
        #start = gc.mem_free()
        beacon_data = TiltStatus(colour, major, _get_decimal_gravity(minor), config)
        #logger.info("cb_tilt_status is:{} bytes".format(start - gc.mem_free()))
        #logger.info("debug: tilt_status:\n{}".format(dir(tilt_status)))
        if not beacon_data.temp_valid:
            logger.warning("Ignoring broadcast due to invalid temperature: {}F".format(beacon_data.temp_fahrenheit))
        elif not beacon_data.gravity_valid:
            logger.warning("Ignoring broadcast due to invalid gravity: " + str(beacon_data.gravity))
        else:
            #logger.info("debug: putting...\n {}".format(dir(beacon_data)))
            #bridge_q.put_nowait(beacon_data)
            #bridge_q.put_sync(beacon_data) #, block=False) # Raises IndexError if the queue is full
            try:
                #await bridge_q.put(beacon_data)
                # testing add to data archive
                data_archive.add_data(colour, major, minor, time.time())
                #logger.info(f"added:{colour}, {major}, {minor}, {time.time()}")
                #data_archive.add_data(colour, sg=1200, tempF=55, tstamp=1724432992)
            except Exception as e:
                logger.error(f"queue put error: {e}")
                raise
            #logger.info("{}\t beacon packet received".format(beacon_data.timestamp))
            #logger.info("debug: bridge_q after {}".format(bridge_q.qsize()))
        #logger.info("debug: end of if colour")
    else:
        #logger.info(f"beacon_callback no colour match: {colour}")
        #todo: log a warning here
        pass


#def _handle_bridge_queue(enabled_providers: list, console_log: bool):
async def _handle_bridge_queue(enabled_providers: list): #, console_log: bool):
    # job to process the queue of data

    try:
        #tilt_status = await bridge_q.get() #blocks until data available
        await asyncio.sleep_ms(100) # testing todo: reduce from 100ms
        for provider in enabled_providers:
            #if provider.upload_due.is_set():
            if provider_timers.upload_is_due(provider):
                logger.debug(f"upload due for {provider}")
                upload_task = asyncio.create_task(provider.update_test())
                await upload_task
                #asyncio.create_task(provider.update_test())
                #provider.upload_due.clear()
                #provider_timers.clear(provider)
    except Exception as e:
        logger.critical(f"handler err: {e}")
        raise
    
    # Log it to console/stdout
    #logger.info("debug SG:{} Temp:{}".format(tilt_status.gravity, tilt_status.temp_celsius))
    #logger.info("SG:{} Temp:{}".format(tilt_status.gravity, tilt_status.temp_celsius))


def _get_decimal_gravity(gravity):
    # gravity will be an int like 1035
    # turn into decimal, like 1.035
    return gravity * .001


def _get_webhook_providers(config: BridgeConfig):
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
        #wlan.country(country)
    wlan.connect(config.ssid, config.password)

    # Wait for connect or fail
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        logger.info('waiting for connection...')
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
        logger.info('connected')
        status = wlan.ifconfig()
        logger.info( 'ip = ' + status[0] )


def get_time(rtc):
    result = False
    try:
        ntptime.settime()
        logger.info("time set to UTC:{}".format(rtc.datetime()))
        result = True
    except:
        # todo catch more specific exception
        logger.info("npttime.settime() failed.")
    return result


def display_time():
    year, month, day, hour, mins, secs, weekday, yearday = time.localtime()
    # logger.info a date - YYYY-MM-DD
    return str("{:02d}:{:02d}:{:02d}".format(hour, mins, secs))


def colour_dict(providers, colours):
    #return the maximum averaging value (seconds) for enabled providers
    # this is how many records from erach tilt that will be saved
    # maybe //5? if Tilt transmits 1/5secs
    # called once per colour?
    # todo each provider could have one different averaging period
    col_max = {}
    max_av = 0
    for provider in providers:
        try:
            for colour in colours:
                if colour in provider.colour_urls.keys() and provider.averaging_period > max_av:
                    max_av = provider.averaging_period
                    col_max[colour] = max_av
        except Exception as e:
            logger.error(f"max_of_averaging error: {s}")
            raise
    #logger.debug(f"col_max: {col_max}")
    return col_max
    
