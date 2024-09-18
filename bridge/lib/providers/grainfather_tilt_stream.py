# GF expects an SG & Temp in Farenheit
# will display on GF website in user preferred units configured in preferences on that platform
# {
#     "SG": 1.034, //this must be a numeric value
#     "Temp: 70, //this must be numeric
# }

import time
import logging
from models import TiltStatus
from models import TiltHistory
#from abstractions import CloudProviderBase
from configuration import BridgeConfig
import asyncio
import async_urequests as requests
import json
import gc # for development only
from machine import Timer


logger = logging.getLogger('GF_tilt_pvdr')
logger.info("Startup")

#class GrainfatherTiltStreamCloudProvider(implements(CloudProviderBase)):
class GrainfatherTiltStreamCloudProvider():

    def __init__(self, config: BridgeConfig):
        self.colour_urls = GrainfatherTiltStreamCloudProvider._normalise_colour_keys(config.grainfather_tilt_stream_urls)
        self.temp_unit = GrainfatherTiltStreamCloudProvider._get_temp_unit(config)
        self.str_name = "Grainfather Tilt URL"
        self.rate = 1
        self.period = (60 * 15)  # 15 minutes
        self.upload_timer = None
        try:
            self.averaging_period = config.grainfather_averaging_period
        except AttributeError:
            self.averaging_period = config.averaging_period
        self.bridge_config = config

    def __str__(self):
        return self.str_name

    def start(self):
        # todo: start is called from main script, but no longer does anything here
        if self.enabled():
            pass

    async def update(self):
        # 
        log_period = self.period//self.rate # older than this = stale data, ensure this is an integer of seconds
        if self.averaging_period > log_period:
            raise Exception(f"Error in config for {self.str_name} provider: Invalid combination of log ({log_period}) & averaging ({self.averaging_period}) periods")
        try:
            for colour in self.colour_urls:
                status, wait_for = [None, None] 
                tempF, SG = self.data_archive.get_data(colour, av_period=self.averaging_period, log_period=log_period)
                if tempF and SG:
                    tilt_status = TiltStatus(colour, tempF, SG, self.bridge_config)
                    status, wait_for = await self.async_update(tilt_status)
                else:
                    logger.info(f"{colour} has no data")
                return [status, wait_for] # either values or [None, None]
                
        except requests.ConnectionError:
            logger.info('requests Connection error. todo: we need a task that periodically ensures WLAN connection is working')
        except Exception as e:
            logger.error(f"exception in provider.update: {e}")
        finally:
            pass
    
    def attach_archive(self, data_archive: TiltHistory):
        # keep a referene to the data queue, this is added after the object is created
        self.data_archive = data_archive
    

    async def async_update(self, tilt_status: TiltStatus):
        start_time = time.ticks_ms()
        if tilt_status.colour in self.colour_urls.keys():
            url = self.colour_urls[tilt_status.colour]
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            payload = self._get_payload(tilt_status)
            gc.collect()
            start = gc.mem_free() #don't call if in a thread?
            #todo handle timeout error
            try:
                response = await requests.post(url, headers=headers, data=json.dumps(payload), timeout=7)
                # do some logging
                status, wait_for = await self.process_response(response, start)
                time_spent = time.ticks_diff(time.ticks_ms(), start_time)
                return [status, wait_for]
            except requests.ConnectionError:
                logger.error("ConnectionError: uploading Grainfather Tilt")
                raise Exception('requests Connection error.')
            except requests.TimeoutError:
                logger.warning("TimeoutError: uploading Grainfather Tilt")
                response = None
                raise Exception("requests Timeout error.") #requests.TimeoutError
                #todo: handle this in the calling function
            finally:  # Usual way to do cleanup 
                pass
 
    def enabled(self):
        return True if self.colour_urls else False

    async def process_response(self, response, start_bytes):
        # check result code
        logger.debug(f"process response {response.status_code}")
        retry_in = None
        if response.status_code == 429:
            # too many requests
            retry_in = int(response.headers.get('retry-after')) # else None
            logger.info(f"URL response:{response.status_code}, reason:{response.reason}, size:{start_bytes - gc.mem_free()}bytes, wait:{retry_in} ")
        elif response.status_code == 200:
            # malformed data?
            logger.warning("URL response:{}, reason:{}, size:{}bytes, text:{}".format(response.status_code, response.reason, start_bytes - gc.mem_free() ))
        elif response.status_code == 201:
            # all good
            logger.debug("URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start_bytes - gc.mem_free()))
        else:
            # some other error
            logger.warning("URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start_bytes - gc.mem_free()))
        await asyncio.sleep_ms(0)
        return [response.status_code, retry_in]

    def _get_payload(self, tilt_status: TiltStatus):
        # GF payload data format
        return {
            "SG": tilt_status.gravity,
            "Temp": tilt_status.temp_fahrenheit
        }
        
    # takes dict of colour->urls
    # returns dict with all colours in lowercase letters for easier matching later
    @staticmethod
    def _normalise_colour_keys(colour_urls):
        normalised_colours = dict()
        if colour_urls is not None:
            for colour in colour_urls:
                normalised_colours[colour.lower()] = colour_urls[colour]

        return normalised_colours

    @staticmethod
    def _get_temp_unit(config: BridgeConfig):
        temp_unit = config.grainfather_temp_unit.upper()
        if temp_unit == "C":
            return "celsius"
        elif temp_unit == "F":
            return "fahrenheit"

        raise ValueError("Grainfather temp unit must be F or C")
