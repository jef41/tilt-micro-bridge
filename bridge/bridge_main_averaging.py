''' works in principle with async 
    could look at running wifi from core1 - doesn't seem to work
    look at running ble collection on core1
    nearly at __version__ 1.0.0
        requires some code tidying - remove comments & old commented out code that is not used
'''
import logging
import gc
import sys
import ntptime
import time
import asyncio
from aioble import central as aioble_central
from bluetooth import UUID
from ubinascii import hexlify
gc.collect()
from primitives import Queue
from machine import RTC
from models import TiltStatus, TiltHistory, iBeaconStatus
from providers import *
from configuration import BridgeConfig
from models.provider_timer import UploadTimers
gc.collect()

logger = logging.getLogger('bridge')

#############################################
# Set up large objects to reserve contiguous space
#############################################

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
            for colour in provider.col_dest.keys():
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
        scanner = asyncio.create_task(_scan_for_ibeacons(simulate=True)) 
        logger.info("started: simulated beacons")
    else:
        # this will generate fake iBeacon data packets - for testing purposes
        logger.info("starting beacon scanner...")
        scanner = asyncio.create_task(_scan_for_ibeacons()) 
        #pass
    try:
        while True:
            # this loop will process the incoming data queue
            # todo: calling handler seems unnecessary?
            handler = asyncio.create_task(_handle_bridge_queue(enabled_providers))
            await handler # wait for handler to return
            await onboard_led.set_status(onboard_led.STATUS_OK) # blink led at 3sec intervals to show running OK
            #asyncio.sleep_ms(100)
    except asyncio.CancelledError:
        print('Trapped cancelled error.')
        raise
    except KeyboardInterrupt:
        # todo: is this actioned here? investigate
        print("cancelling tasks...")
        handler.cancel()
        scanner.cancel()
    except Exception as e:
        logger.info(f"Error in bridge_main: {e}")
        raise


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
        if simulate: # and pckt_complete:
            # generate a fake beacon signal
            #pckt_complete = False
            #logger.info(f"MAC: {result.device.addr_hex()} Not beacon: {result.rssi}")
            # fake callback
            #from random import randrange
            #uuid = choice(list(uuid_to_colours.keys()))
            try:
                col = (randrange(0x10, 0xA0, 0x10)).to_bytes(1,'big')
            except NameError:
                from random import randrange
                col = (randrange(0x10, 0xA0, 0x10)).to_bytes(1,'big')
            #print(col)
            major = (randrange(700, 750)).to_bytes(2,'big') # (500, 850) HD ->SD (50, 85)
            minor = (randrange(10150, 10350)).to_bytes(2,'big') # (10050, 10450) HD -> SD (1005, 1045)
            pre = b'\x02\x01\x04\x1a\xffL\x00\x02\x15\xa4\x95\xbb'
            post = b'\xc5\xb1KD\xb5\x12\x13p\xf0-t\xde'
            tx_pwr = b'\x00'
            adv_data = b''.join([pre, col, post, major, minor, tx_pwr])
            #print(adv_data)
            iBeacon_data = iBeaconStatus(adv_data, 0, "00:00:00:00:00:00")
            #await _beacon_callback(uuid, major, minor, 0, 0, simulate)#, bridge_q)
            #print(f'{iBeacon_data.colour} {col} {iBeacon_data.major} {iBeacon_data.minor}')
            try:
                task = asyncio.create_task(_beacon_callback(iBeacon_data, simulate))
                #task running
                await asyncio.sleep_ms(randrange(80, 120)) # pause here & give way
                await task # then wait for task to complete
                #res = await asyncio.gather(t1,t2, return_exceptions=True)
            except asyncio.TimeoutError:  # These only happen if return_exceptions is False
                print('Timeout')  # With the default times, cancellation occurs first
            except asyncio.CancelledError:
                print('Cancelled')
            #asyncio.sleep_ms(randrange(100, 750))
            #pckt_complete = True
        else:
            async with aioble_central.scan(duration_ms=5000, 
                                           interval_us=100_000,
                                           window_us=100_000, active=True) as scanner:
                # scan for real beacons
                try:
                    async for result in scanner:
                        if result.adv_data and result.adv_data[5:11] == iBeacon_prefix:
                            #print("match")
                            rssi = result.rssi
                            # Extract and process iBeacon data
                            #await _beacon_callback(iBeacon_data, rssi, simulate)
                            iBeacon_data = iBeaconStatus(result.adv_data, result.rssi, result.device.addr_hex())
                            #print(iBeacon_data)
                            await _beacon_callback(iBeacon_data, simulate)
                        #else:
                        #    if result.name():
                        #        #print(dir(result.manufacturer()))
                        #        print(f"{list(result.services())} name: {result.name()}")
                     
                except AttributeError:
                    #logger.info(f"scanner result is:{result} scanner is:{scanner}")
                    #logger.info(f"scanner result.adv_data is {result.adv_data}")
                    logger.info(f"Attribute Error in bridge scanner")
                    #raise
            #asyncio.sleep_ms(800 if simulate else 10) # don't flood with simulated beacons
           
        
        asyncio.sleep_ms(100)


async def _beacon_callback(iBeacon_packet, simulated):
    global data_archive
    # todo: this isn't actually an async routine
    # check bluetooth data and store on a queue (TiltHistory object)

    if iBeacon_packet.colour in data_archive.ringbuffer_list:
        #logger.info("beacon_callback colour match, {}".format(colour))
        # iBeacon packets have major/minor attributes with data
        # major = degrees in F (int)
        # minor = gravity (int) - needs to be converted to float (e.g. 1035 -> 1.035)
        #start = gc.mem_free()
        gc.collect() #testing
        beacon_data = TiltStatus(iBeacon_packet.colour, iBeacon_packet.major, _get_decimal_gravity(iBeacon_packet.minor), config, raw=True)
        #logger.info("cb_tilt_status is:{} bytes".format(start - gc.mem_free()))
        #logger.info("debug: tilt_status:\n{}".format(dir(tilt_status)))
        if not beacon_data.temp_valid:
            logger.warning(f"Ignoring broadcast due to invalid temperature: {beacon_data.temp_fahrenheit}°F")
        elif not beacon_data.gravity_valid:
            logger.warning(f"Ignoring broadcast due to invalid gravity: {beacon_data.gravity}" )
        else:
            # seems to be a valid packet, if 1st packet, make a note
            # peekq returns a memoryview - if it is all 0 then this is the first packet
            if ( data_archive.ringbuffer_list[beacon_data.colour] and
                 all(b == 0 for b in data_archive.ringbuffer_list[beacon_data.colour].peekq()[0:7])
               ):
                logger.info(f"received from new Tilt; {beacon_data.colour[0].upper() + beacon_data.colour[1:]}, MAC:{iBeacon_packet.mac}, RSSI:{iBeacon_packet.rssi}" )
            if data_archive.print_raw:
                # check if we should print raw values as they are received (useful for calibration)
                logger.debug(f"data: {iBeacon_packet.colour} SG:{beacon_data.gravity:.4f} {beacon_data.temp_fahrenheit:.1f}°F")
            
            try:
                #await bridge_q.put(beacon_data)
                # add raw to data archive (for size, storing integer values for Temp & Gravity 1040, not 1.040 not calibrated vals))
                data_archive.add_data(iBeacon_packet.colour, iBeacon_packet.major, iBeacon_packet.minor, time.time())
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


async def _handle_bridge_queue(enabled_providers: list): #, console_log: bool):
    # job to process the queue of data
    try:
        #tilt_status = await bridge_q.get() #blocks until data available
        await asyncio.sleep_ms(10) # testing todo: reduce from 100ms
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
    # todo: maybe //5? if Tilt transmits 1/5secs
    # called once per colour?
    col_max = {}
    max_av = 0
    try:
        for provider in providers:
            #print(f"***  colours {colours}")
            for colour in colours:
                #print(f"***  test {provider}: {colour}, {provider.col_dest.keys()}")
                if colour in provider.col_dest.keys() and provider.averaging_period >= max_av -1:
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
