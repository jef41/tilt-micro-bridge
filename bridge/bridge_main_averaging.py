''' works in principle with async 
    could look at running wifi from core1 - doesn't seem to work
    look at running ble collection on core1
'''
import logging
import gc
import sys
import ntptime
#import network
import time
import asyncio
from aioble import central as aioble_central
from bluetooth import UUID
from ubinascii import hexlify
gc.collect()
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
gc.collect()
#debug_recvd_counter = 0  #for dev purposes, need a better implementation
#_TILT_UUID = bluetooth.UUID("a495bb60c5b14b44b5121370f02d74de")

logger = logging.getLogger('bridge')
'''
if "RP2040" in  sys.implementation._machine:
    import rp2
    RP2040 = True
else:
    RP2040 = False
    #network.country(country)
'''
#############################################
# Statics
#############################################
uuid_to_colours = {
        UUID("a495bb20-c5b1-4b44-b512-1370f02d74de"): "green",
        UUID("a495bb30-c5b1-4b44-b512-1370f02d74de"): "black", 
        UUID("a495bb10-c5b1-4b44-b512-1370f02d74de"): "red",
        UUID("a495bb60-c5b1-4b44-b512-1370f02d74de"): "blue",
        UUID("a495bb50-c5b1-4b44-b512-1370f02d74de"): "orange",
        UUID("a495bb70-c5b1-4b44-b512-1370f02d74de"): "yellow",
        UUID("a495bb40-c5b1-4b44-b512-1370f02d74de"): "purple",
        UUID("a495bb80-c5b1-4b44-b512-1370f02d74de"): "pink",
        UUID("a495bb40-c5b1-4b44-b512-1370f02d74df"): "simulated"  # reserved for fake beacons during simulation mode
    }

colours_to_uuid = dict((v, k) for k, v in uuid_to_colours.items())

# Load config from file, with defaults, and args
config = BridgeConfig.load()

#reserve some space for the tilt_status object
gc.collect()
# Queue for holding incoming data from scans
data_archive = bytearray()


normal_providers = [
        #PrometheusCloudProvider(config),
        CSVFileProvider(config),
        #InfluxDbCloudProvider(config),
        #InfluxDb2CloudProvider(config),
        #BrewfatherCustomStreamCloudProvider(config),
        #BrewersFriendCustomStreamCloudProvider(config),
        GrainfatherCustomStreamCloudProvider(config),
        GrainfatherTiltStreamCloudProvider(config),
        #TaplistIOCloudProvider(config),
        #AzureIoTHubCloudProvider(config)
    ]


provider_timers = UploadTimers() # reference to all enabled provder timers
handler = None					 # reference to data handler task
scanner = None					 # reference to bluetooth scanner task

# initiate RTC object
rtc = RTC()


#############################################


async def bridge_main(onboard_led, providers, simulate_beacons: bool = False):
    # todo remove providers here too?
    global data_archive
    global provider_timers
    global handler
    global scanner
    if providers is None:
        providers = normal_providers
    # add any webhooks defined in config
    # todo !! not currently implemented/tested
    webhook_providers = _get_webhook_providers(config)
    if webhook_providers:
        providers.extend(webhook_providers)
    # Start cloud providers
    logger.info("Starting...")
    enabled_providers = list()
    enabled_colours = list()
    # get configured providers & associated Tilt device colours
    for provider in providers:
        if provider.enabled():
            enabled_providers.append(provider)
            provider__start_message = provider.start() #todo look into this
            if not provider__start_message:
                provider__start_message = ''
            logger.info("...started: {} {}".format(provider, provider__start_message))
            # find configured colours
            for colour in provider.colour_urls.keys():
                if colour not in enabled_colours:
                    enabled_colours.append(colour)
    
    gc.collect()
    # for debug, intermittently log memory usage/leak
    asyncio.create_task(debug_memory())
    
    # size the TiltHistory object for each colour accordingly
    # and create upload timers
    data_archive = TiltHistory(max_av_period(enabled_providers, enabled_colours))
    
    #logger.debug("data archive created")
    try:
        for provider in enabled_providers:
            provider.attach_archive(data_archive)
            logger.debug(f"attached archive for {provider}")
            logger.debug(f"add timer with log_period:{provider.period} averaging_period:{provider.averaging_period} secs")
            provider_timers.add(provider, provider.period, provider.averaging_period)
            logger.debug(f"created timer for {provider}")
    except Exception as e:
        logger.debug(f"Exception: {e}")
    
    # Start scanning for Tilt data
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
        #a = 12000 # for debugging
        while True:
            # this loop will process the incoming data queue
            # todo: calling handler seems unnecessary?
            #handler = asyncio.create_task(_handle_bridge_queue(bridge_q, console_log))
            handler = asyncio.create_task(_handle_bridge_queue(enabled_providers)) #, console_log))
            await handler # wait for handler to return
            #await onboard_led.change_rate(10, 3000) # blink led at 3sec intervals to show running OK
            await onboard_led.set_status(onboard_led.STATUS_OK) # blink led at 3sec intervals to show running OK
            #asyncio.sleep_ms(100)
    except asyncio.CancelledError:
        print('Trapped cancelled error.')
        raise
    except KeyboardInterrupt:
        # todo: is this actioned here? investigate
        handler.cancel()
        scanner.cancel()
    except Exception as e:
        logger.info(f"Error in bridge_main: {e}")
        raise
    #logger.info("...started: Tilt scanner")


async def _scan_for_ibeacons(simulate=False):
    ''' '''
    #global bridge_q
    #logger.info("debug: starting scanner...")
    # Constants for iBeacon
    iBeacon_prefix = b'\x4C\x00\x02\x15\xa4\x95'  # Apple company ID + iBeacon type + 2 bytes of Tilt uuid
    # Tilt format based on iBeacon format with Tilt specific uuid preamble (a495)
    #TILT = "0215a495"
    # Start scanning for advertisements
    while True:
        async with aioble_central.scan(duration_ms=5000, 
                                       interval_us=100_000,
                                       window_us=100_000, active=True) as scanner:
            try:
                async for result in scanner: 
                    #if result.name():
                    #    print(result, result.name(), result.rssi, result.services())
                    # Check if the advertisement contains the iBeacon prefix
                    #if result.manufacturer and result.manufacturer.startswith(IBEACON_PREFIX):
                    #mac = result.addr
                    if result.adv_data and result.adv_data[5:11]==iBeacon_prefix:
                        #print("match")
                        rssi = result.rssi
                        
                        #try:
                        #    logger.info(f"MAC: {result.device.addr_hex()}")#, {iBeacon_data.uuid}")
                        #except Exception as e:
                        #    print(e)
                        
                        #adv_data = result.adv_data
                        '''
                        uuid = bluetooth.UUID(''.join(['{:02X}'.format(b) for b in adv_data[9:25]]))
                        #uuid = uuid1   # UUID (16 bytes)
                        major = int.from_bytes(adv_data[25:27], 'big')  # Major (2 bytes) Temp
                        minor = int.from_bytes(adv_data[27:29], 'big')  # Minor (2 bytes) SG
                        tx_power = int.from_bytes(adv_data[29:], 'big', True) # signed=True)  # TX Power (1 byte)
                        '''
                        # Extract and process iBeacon data
                        iBeacon_data = build_iBeacon_packet(result.adv_data)
                        #print(iBeacon_data)
                        # Call the callback function with the extracted data
                        await _beacon_callback(iBeacon_data, rssi, simulate)#, bridge_q)
                        #_beacon_callback("a495bb40-c5b1-4b44-b512-1370f02d74df", 65, 1021, 0, 0, bridge_q)
                    #else:
                    #    if result.name():
                    #        #print(dir(result.manufacturer()))
                    #        print(f"{list(result.services())} name: {result.name()}")
                    if simulate:
                        #logger.info(f"MAC: {result.device.addr_hex()} Not beacon: {result.rssi}")
                        # fake callback
                        from random import randrange, choice
                        uuid = choice(list(uuid_to_colours.keys()))
                        major = randrange(700, 750) # (500, 850) HD ->SD (50, 85)
                        minor = randrange(10150, 10350) # (10050, 10450) HD -> SD (1005, 1045)
                        await _beacon_callback(uuid, major, minor, 0, 0, simulate)#, bridge_q)
                        #pass # testing is it scanner or callback that causes issue? or maybe colours_to_uuid def?
            except AttributeError:
                #logger.info(f"scanner result is:{result} scanner is:{scanner}")
                #logger.info(f"scanner result.adv_data is {result.adv_data}")
                logger.info(f"Attribute Error in bridge scanner")
                #raise
        asyncio.sleep_ms(100)


#def _beacon_callback(bt_addr, rssi, packet, additional_info, bridge_q):
async def _beacon_callback(iBeacon_packet, rssi, simulated):#, bridge_q):
    global data_archive
    # todo: this isn't actually an async routine
    # check bluetooth data and store on a queue (TiltHistory object)
    #    return
    #global debug_recvd_counter
    #print(iBeacon_packet)
    try:
        colour = uuid_to_colours.get(iBeacon_packet['uuid'])
    except Exception as e:
        print(e)
    if colour in data_archive.ringbuffer_list:
        #logger.info("beacon_callback colour match, {}".format(colour))
        # iBeacon packets have major/minor attributes with data
        # major = degrees in F (int)
        # minor = gravity (int) - needs to be converted to float (e.g. 1035 -> 1.035)
        #start = gc.mem_free()
        gc.collect() #testing
        beacon_data = TiltStatus(colour, iBeacon_packet['major'], _get_decimal_gravity(iBeacon_packet['minor']), config, raw=True)
        #logger.info("cb_tilt_status is:{} bytes".format(start - gc.mem_free()))
        #logger.info("debug: tilt_status:\n{}".format(dir(tilt_status)))
        if not beacon_data.temp_valid:
            logger.warning(f"Ignoring broadcast due to invalid temperature: {beacon_data.temp_fahrenheit}°F")
        elif not beacon_data.gravity_valid:
            logger.warning(f"Ignoring broadcast due to invalid gravity: {beacon_data.gravity}" )
        else:
            if data_archive.print_raw:
                # check if we should print raw values as they are received (useful for calibration)
                logger.debug(f"data: {colour} SG:{beacon_data.gravity:.4f} {beacon_data.temp_fahrenheit:.1f}°F")
            
            try:
                #await bridge_q.put(beacon_data)
                # add raw to data archive (for size, storing integer values for Temp & Gravity 1040, not 1.040 not calibrated vals))
                data_archive.add_data(colour, iBeacon_packet['major'], iBeacon_packet['minor'], time.time())
                #logger.info(f"added:{colour}, {major}, {minor}, {time.time()}")
            except Exception as e:
                logger.error(f"queue put error: {e}")
                raise
            #logger.info("{}\t beacon packet received".format(beacon_data.timestamp))
    else:
        # if simulated !+ true then warn about unconfigured Tilt
        if simulated == False:
            logger.warning(f"data received for an unconfigured Tilt: {colour}")
        #pass



#def _handle_bridge_queue(enabled_providers: list, console_log: bool):
async def _handle_bridge_queue(enabled_providers: list): #, console_log: bool):
    # job to process the queue of data

    try:
        #tilt_status = await bridge_q.get() #blocks until data available
        await asyncio.sleep_ms(0) # testing todo: reduce from 100ms
        for provider in enabled_providers:
            #if provider.update_in_progress:
            #    logger.debug(f"{provider} update already in progress")
            if provider_timers.upload_is_due(provider): # and not provider.update_in_progress:
                logger.debug(f"update due for {provider}")
                #upload_task = asyncio.create_task(provider.update())
                #await upload_task
                response_code, wait_for_secs = await provider.update()
                # provider.update must return a2 values, code & wait - can be None
                #logger.debug(f"got: response;{response_code}, wait:{wait_for_secs}")
                # upload_task should return the [response code, seconds to wait] if a 429 response
                # response code logging should be managed in provider module
                #if upload_task[0] == 429:
                #    provider_timers.adjust(provider, upload_task[1])
                if response_code == 429 and wait_for_secs > 0:
                    #todo: if wait_for is 0 then when do we retry?
                    #logger.debug(f"adjust timer: {wait_for_secs}")
                    provider_timers.adjust(provider, wait_for_secs)
    except StopIteration:
        # no data received
        logger.warning("Upload due, but no data available")
        await asyncio.sleep_ms(1000)
        #raise
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


def max_av_period(providers, colours):
    #return the maximum averaging value (seconds) for enabled providers
    # this is how many records from each tilt that will be saved
    col_max = {}
    max_av = 0
    try:
        for provider in providers:
            #print(f"***  colours {colours}")
            for colour in colours:
                #print(f"***  test {provider}: {colour}, {provider.colour_urls.keys()}")
                if colour in provider.colour_urls.keys() and provider.averaging_period >= max_av -1:
                    #print(f"***   colour match: {colour}")
                    max_av = provider.averaging_period + 1 # so if passed 0 then this will still work
                    col_max[colour] = max_av
                    #print(f"***   {col_max}")
                else:
                    #print(f"***   no match {colour} av_period {provider.averaging_period}")
                    pass
    except Exception as e:
        logger.error(f"max_av_period error: {e}")
        raise
    #logger.debug(f"col_max: {col_max}")
    return col_max
    
async def debug_memory():
    # intermittently log memory usage, every 30 mins
    while True:
        await asyncio.sleep(30 * 60)
        logger.debug(f"gc: {gc.mem_free()}")


def build_iBeacon_packet(d):
    # 
    uuid = UUID(''.join(['{:02X}'.format(b) for b in d[9:25]]))
    major = int.from_bytes(d[25:27], 'big')  # Major (2 bytes) Temp
    minor = int.from_bytes(d[27:29], 'big')  # Minor (2 bytes) SG
    tx_power = int.from_bytes(d[29:], 'big', True) # signed=True)  # TX Power (1 byte)
    return { "uuid":uuid, "major":major, "minor":minor, "tx_power":tx_power }
