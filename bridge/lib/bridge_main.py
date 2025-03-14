"""central handler holds most coros & passes data between
1.0.1 use enabled_tilts instead of colours_enabled - needs test
TODO track how to store HD or SD
"""

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
import machine
from machine import RTC, WDT, WDT_RESET
from models import TiltStatus, TiltHistory, iBeaconStatus
from providers import *
from configuration import BridgeConfig
from models.provider_timer import UploadTimers

gc.collect()


class TiltDevice:
    def __init__(self, colour):
        self.colour = colour
        self.rssi = None
        self.hd = None
        self.extended = None


class BridgeMain:
    logger = logging.getLogger("bridge")

    def __init__(self):
        self.config = None
        self.providers = None
        self.data_archive = bytearray()  # Queue for holding incoming data from scans
        self.provider_timers = UploadTimers()  # reference to all enabled provder timers
        self.handler = None  # reference to data handler task
        self.scanner = None  # reference to bluetooth scanner task
        self.lcd_updater = None  # reference to a lcd updater task
        self.enabled_providers = list()
        self.enabled_tilts = list()
        self.rtc = None
        self.wdt = None
        self.onboard_led = None
        self.rgb_led = None
        self.display = None
        self.check_for_display()
        # Load config from file, with defaults, and args
        result = True
        gc.collect()
        try:
            self.config = BridgeConfig.load()
        except ValueError as e:
            self.logger.critical("Error in the Config JSON file")
            result = False
        except Exception as e:
            self.logger.critical(e)
            result = False
        if result:
            # gc.collect()
            self.rtc = RTC()

    def check_for_display(self):
        # try block to load pimoroni display & libs
        # also read pin mappings for disaply (& lcd)
        # also set rgb_led & dispaly, if present
        pass

    def initialised(self):
        return self.rtc

    async def bridge_main(self, onboard_led, simulate_beacons: bool = False):
        gc.collect()
        self.onboard_led = onboard_led
        # if providers is None:
        #    self.providers = self.set_providers()
        # else:
        #    self.providers = providers
        # add any webhooks defined in config
        # todo !! not currently implemented/tested
        self.webhook_providers = self._get_webhook_providers()

        if self.webhook_providers:
            self.providers.extend(self.webhook_providers)
        # Start cloud providers
        self.logger.info("Starting...")
        asyncio.create_task(self._init_watchdog())
        # set log flush timer
        asyncio.create_task(BridgeMain._force_logging())
        # get configured providers & associated Tilt device colours
        for provider in self.providers:
            if provider.enabled():
                self.enabled_providers.append(provider)
                provider__start_message = provider.start()  # todo look into this
                if not provider__start_message:
                    provider__start_message = ""
                self.logger.info(f"...started: {provider} {provider__start_message}")
                # find configured colours, or add to list
                # if colour not in self.enabled_tilts:
                #    if colour not in self.enabled_tilts.get('colour'):
                #    self.enabled_tilts.append(colour)
                for colour in provider.col_dest.keys():
                    # if not next((device for device in self.enabled_tilts if device.colour == colour), None):
                    if not any(
                        device.colour == colour for device in self.enabled_tilts
                    ):
                        self.enabled_tilts.append(TiltDevice(colour))

        # for debug, intermittently log memory usage/leak
        if logging.getLogger().level < logging.INFO:
            asyncio.create_task(debug_memory(self.logger))

        # size the TiltHistory object for each colour accordingly
        # and create upload timers
        gc.collect()
        self.data_archive = TiltHistory(
            max_av_period(self.enabled_providers, self.enabled_tilts)
        )
        self.logger.info(
            f"Received Tilt data packets will be printed to stdout for {self.data_archive.results_secs}secs"
        )
        try:
            for provider in self.enabled_providers:
                provider.attach_archive(self.data_archive)
                self.logger.debug(f"attached archive for {provider}")
                self.logger.debug(
                    f"add timer with log_period:{provider.period} averaging_period:{provider.averaging_period} secs"
                )
                self.provider_timers.add(
                    provider, provider.period, provider.averaging_period
                )
                self.logger.debug(f"created timer for {provider}")
        except Exception as e:
            self.logger.debug(f"Exception: {e}")

        # Start scanning for Tilt data
        if simulate_beacons:
            # this will generate fake iBeacon data packets - for testing purposes
            self.scanner = asyncio.create_task(self._scan_for_ibeacons(simulate=True))
            self.logger.info("started: simulated beacons")
        else:
            self.logger.info("starting beacon scanner...")
            self.scanner = asyncio.create_task(self._scan_for_ibeacons())
            # pass
        try:
            await self.onboard_led.set_status(
                self.onboard_led.STATUS_OK
            )  # blink led at 3sec intervals to show running OK
            if self.display:
                # start a background task to update the lcd screen
                # self.lcd_updater = asyncio.create_task(lcd_updater(enabled_tilts)) #colour, rssi, extended, hd
                pass
            while True:
                # this loop will process the incoming data queue
                self.handler = asyncio.create_task(self._handle_bridge_queue())
                await self.handler  # wait for handler to return
                # asyncio.sleep_ms(100)
        except asyncio.CancelledError:
            print("Trapped cancelled error.")
            raise
        except KeyboardInterrupt:
            # this is not usually actioned here, calling async coro captures the KB interrupt
            print("cancelling tasks...")
            self.handler.cancel()
            self.scanner.cancel()
        except Exception as e:
            self.logger.info(f"Error in bridge_main: {e}")
            raise

    async def _scan_for_ibeacons(self, simulate=False):
        """scan for iBeacons with Tilt prefix"""
        # logger.info("debug: starting scanner...")
        iBeacon_prefix = b"\x4c\x00\x02\x15\xa4\x95"  # Apple company ID + iBeacon type + 2 bytes of Tilt uuid
        # Tilt format based on iBeacon format with Tilt specific uuid preamble (a495)
        # Start scanning for advertisements
        while True:
            if simulate:
                # generate a fake beacon signal
                try:
                    col = (randrange(0x10, 0xA0, 0x10)).to_bytes(1, "big")
                except NameError:
                    from random import randrange

                    col = (randrange(0x10, 0xA0, 0x10)).to_bytes(1, "big")
                major = (randrange(700, 750)).to_bytes(
                    2, "big"
                )  # (500, 850) HD/SD (500, 850)
                minor = (randrange(10150, 10350)).to_bytes(
                    2, "big"
                )  # (10050, 10450) HD -> SD (1005, 1045)
                pre = b"\x02\x01\x04\x1a\xffL\x00\x02\x15\xa4\x95\xbb"
                post = b"\xc5\xb1KD\xb5\x12\x13p\xf0-t\xde"
                tx_pwr = b"\x00"
                adv_data = b"".join([pre, col, post, major, minor, tx_pwr])
                # print(adv_data)
                iBeacon_data = iBeaconStatus(adv_data, 0, "00:00:00:00:00:00")
                # await _beacon_callback(uuid, major, minor, 0, 0, simulate)#, bridge_q)
                # print(f'{iBeacon_data.colour} {col} {iBeacon_data.major} {iBeacon_data.minor}')
                try:
                    task = asyncio.create_task(
                        self._beacon_callback(iBeacon_data, simulate)
                    )
                    # task running
                    await asyncio.sleep_ms(randrange(80, 120))  # pause here & give way
                    await task  # then wait for task to complete
                    # res = await asyncio.gather(t1,t2, return_exceptions=True)
                except (
                    asyncio.TimeoutError
                ):  # These only happen if return_exceptions is False
                    logger.warning(
                        "scanner Timeout"
                    )  # With the default times, cancellation occurs first
                except asyncio.CancelledError:
                    logger.warning("scanner Cancelled")
                # asyncio.sleep_ms(randrange(100, 750))
                # pckt_complete = True
            else:
                async with aioble_central.scan(
                    duration_ms=5000,
                    interval_us=100_000,
                    window_us=100_000,
                    active=True,
                ) as scanner:
                    # scan for real beacons
                    try:
                        async for result in scanner:
                            if (
                                result.adv_data
                                and result.adv_data[5:11] == iBeacon_prefix
                            ):
                                # Extract and process iBeacon data
                                iBeacon_data = iBeaconStatus(
                                    result.adv_data,
                                    result.rssi,
                                    result.device.addr_hex(),
                                )
                                # print(iBeacon_data)
                                await self._beacon_callback(iBeacon_data, simulate)

                    except AttributeError:
                        # logger.info(f"scanner result is:{result} scanner is:{scanner}")
                        # logger.info(f"scanner result.adv_data is {result.adv_data}")
                        self.logger.info(f"Attribute Error in bridge scanner")
                        # raise
                # asyncio.sleep_ms(800 if simulate else 10) # don't flood with simulated beacons

            if self.wdt:
                self.wdt.feed()
            asyncio.sleep_ms(100)

    async def _beacon_callback(self, iBeacon_packet, simulated):
        """check bluetooth data and store on a queue (TiltHistory object)"""
        # todo: this isn't actually an async routine

        if iBeacon_packet.colour in self.data_archive.ringbuffer_list:
            # logger.info("beacon_callback colour match, {}".format(colour))
            # iBeacon packets have major/minor attributes with data
            # major = degrees in F (int)
            # minor = gravity (int) - needs to be converted to float (e.g. 1035 -> 1.035)
            # hd = True if sg_float > 2 else False
            beacon_data = TiltStatus(
                iBeacon_packet.colour,
                iBeacon_packet.major,
                BridgeMain._get_decimal_gravity(iBeacon_packet.minor),
                self.config,
                apply_calibration=False,
            )
            # logger.info("cb_tilt_status is:{} bytes".format(start - gc.mem_free()))
            # logger.info("debug: tilt_status:\n{}".format(dir(tilt_status)))
            if not beacon_data.temp_valid:
                self.logger.warning(
                    f"Ignoring broadcast due to invalid temperature: {beacon_data.temp_fahrenheit:.2g}°F"
                )
            elif not beacon_data.gravity_valid:
                self.logger.warning(
                    f"Ignoring broadcast due to invalid gravity: {beacon_data.gravity:.5g}"
                )
            else:
                # seems to be a valid packet
                if self.rgb_led:
                    # async routine/task to flash the led the correct colour
                    # asyncio.create_task(lcd.rgb_led_flash(iBeacon_packet.colour))
                    pass
                # update tilt_enabled dict with RSSI
                try:
                    match_device = next(
                        device
                        for device in self.enabled_tilts
                        if device.colour == iBeacon_packet.colour
                    )
                    match_device.rssi = iBeacon_packet.rssi
                    match_device.hd = beacon_data.hd
                    match_device.extended = (
                        True if beacon_data.original_gravity else False
                    )
                except StopIteration:
                    match_device = None
                # peekq returns a memoryview - if it is all 0 then this is the first packet
                # if 1st packet, make a note
                if self.data_archive.ringbuffer_list[beacon_data.colour] and all(
                    b == 0
                    for b in self.data_archive.ringbuffer_list[
                        beacon_data.colour
                    ].peekq()[0:7]
                ):
                    self.logger.info(
                        f"received from new Tilt; {beacon_data.colour[0].upper() + beacon_data.colour[1:]}, MAC:{iBeacon_packet.mac}, RSSI:{iBeacon_packet.rssi}"
                    )
                if self.data_archive.print_raw:
                    # check if we should print raw values to std out as they are received (useful for calibration)
                    n = 4 if beacon_data.hd else 3
                    print(
                        f"data: {iBeacon_packet.colour} SG:{beacon_data.gravity:.{n}f} {beacon_data.temp_fahrenheit:.1f}°F"
                    )

                try:
                    # await bridge_q.put(beacon_data)
                    # add raw to data archive (for size, storing integer values for Temp & Gravity 1040, not 1.040 not calibrated vals))
                    self.data_archive.add_data(
                        iBeacon_packet.colour,
                        iBeacon_packet.major,
                        iBeacon_packet.minor,
                        time.time(),
                    )
                    # logger.info(f"added:{colour}, {major}, {minor}, {time.time()}")

                except Exception as e:
                    self.logger.error(f"queue put error: {e}")
                    raise
                # logger.info("{}\t beacon packet received".format(beacon_data.timestamp))
        else:
            # if simulated != true then warn about unconfigured Tilt
            if simulated == False:
                self.logger.warning(f"data received for an unconfigured Tilt: {colour}")
            # pass

    async def _handle_bridge_queue(self):
        # job to process the queue of data
        try:
            await asyncio.sleep_ms(100)
            for provider in self.enabled_providers:
                # if provider.update_in_progress:
                #    self.logger.debug(f"{provider} update already in progress")
                if self.provider_timers.upload_is_due(
                    provider
                ):  # and not provider.update_in_progress:
                    self.logger.debug(f"update due for {provider}")
                    # await upload_task TODO call with a timeout?
                    response_code, wait_for_secs = await provider.update()
                    # provider.update must return 2 values, code & wait - can be None
                    # TODO more generic handling of response codes, or handle them per provider - pass provider_timer to provider
                    # if response_code == 429 and wait_for_secs > 0:
                    if wait_for_secs:
                        # todo: if wait_for is 0 then when do we retry?
                        # logger.debug(f"adjust timer: {wait_for_secs}")
                        self.provider_timers.adjust(provider, wait_for_secs)
        except StopIteration:
            # no data received
            self.logger.warning("Upload due, but no data available")
            await asyncio.sleep_ms(1000)
            # raise
        except Exception as e:
            self.logger.critical(f"handler err: {e}")
            raise
        # Log it to console/stdout
        # logger.info("debug SG:{} Temp:{}".format(tilt_status.gravity, tilt_status.temp_celsius))
        # logger.info("SG:{} Temp:{}".format(tilt_status.gravity, tilt_status.temp_celsius))

    @staticmethod
    async def _force_logging():
        # ensure the logger is flushed after initial startup
        await asyncio.sleep(12)
        logging.getLogger().handlers[0].current_log_file.flush()

    async def _init_watchdog(self):
        # global wdt
        cause = (
            "PWRON_RESET",
            "HARD_RESET",
            "WDT_RESET",
            "DEEPSLEEP_RESET",
            "SOFT_RESET",
        )
        # print('WDT routine called')
        reset_reason = machine.reset_cause()
        self.logger.info(f"machine.reset_cause: {cause[reset_reason - 1]}")
        # if reset_reason == WDT_RESET:
        #    TODO try upload asap
        if logging.getLogger().level > 10:
            # only enable wdt if we are not debugging
            # wait 1 hour before starting wdt - allow user time to do calibration/tests without device constantly restarting
            await asyncio.sleep(3600)
            self.wdt = WDT(timeout=8388)
            self.logger.info("WDT started")
        else:
            self.logger.debug("WDT not initiated")

    @staticmethod
    def _get_decimal_gravity(gravity):
        # gravity will be an int like 1035
        # turn into decimal, like 1.035
        return gravity * 0.001

    def _get_webhook_providers(self):
        # Multiple webhooks can be fired, so create them dynamically and add to
        # all providers static list
        webhook_providers = list()
        for url in self.config.webhook_urls:
            webhook_providers.append(WebhookCloudProvider(url, self.config))
        return webhook_providers

    def set_providers(self, network=False):
        if network:
            normal_providers = [
                # PrometheusCloudProvider(self.config),
                CSVFileProvider(self.config),
                # InfluxDbCloudProvider(self.config),
                # InfluxDb2CloudProvider(self.config),
                # BrewfatherCustomStreamCloudProvider(self.config),
                # BrewersFriendCustomStreamCloudProvider(self.config),
                GrainfatherCustomStreamCloudProvider(self.config),
                GrainfatherTiltStreamCloudProvider(self.config),
                # TaplistIOCloudProvider(self.config),
                # AzureIoTHubCloudProvider(self.config)
            ]
        else:
            normal_providers = [
                CSVFileProvider(self.config),
            ]
            self.logger.warning(
                "No network credentials specified. Enabling local CSV logging only."
            )
        self.providers = normal_providers

    def get_time(self):
        result = False
        try:
            ntptime.settime()
            self.logger.info("time set to UTC:{}".format(self.rtc.datetime()))
            result = True
        except:
            # todo catch more specific exception
            self.logger.info("npttime.settime() failed.")
        return result


def max_av_period(providers, tilt_devices):
    # return the maximum averaging value (seconds) for enabled providers
    # this is how many records from each tilt that will be saved
    col_max = {}
    max_av = 30  # set a minimum store size of 30 readings
    try:
        for provider in providers:
            # print(f"***  colours {colours}")
            for device in tilt_devices:
                # print(f"***  test {provider}: {colour}, {provider.col_dest.keys()}")
                if (
                    device.colour in provider.col_dest.keys()
                    and provider.averaging_period > max_av
                ):
                    max_av = provider.averaging_period
                    # print(f"***   {col_max}")
                else:
                    # print(f"***   no match {colour} av_period {provider.averaging_period}")
                    pass
                col_max.update({device.colour: max_av})
    except Exception as e:
        # logger.error(f"max_av_period error: {e}")
        raise
    # print(f"col_max: {col_max}")
    return col_max


async def debug_memory(logger):
    # intermittently log memory usage, every 30 mins
    while True:
        await asyncio.sleep(30 * 60)
        logger.debug(f"gc: {gc.mem_free()}")


__version__ = "1.0.1"
