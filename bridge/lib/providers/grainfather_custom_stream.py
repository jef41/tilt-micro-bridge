# Payload docs are found by clicking the "info" button next to a fermenation device on grainfather.com
# {
#     "specific_gravity": 1.034, //this must be a numeric value
#     "temperature": 18, //this must be numeric
#     "unit": "celsius" || "fahrenheit" //supply the unit that matches the temperature you are sending
# }

import time
import logging
from models import TiltStatus
from models import TiltHistory
from abstractions import BridgeProviderBase
from configuration import BridgeConfig
import asyncio
import async_urequests as requests
import json
import gc # for development only
from machine import Timer


logger = logging.getLogger('GFcstm_pvdr')
logger.info("Startup")

class GrainfatherCustomStreamCloudProvider(BridgeProviderBase):

    def __init__(self, config: BridgeConfig):
        self.col_dest = GrainfatherCustomStreamCloudProvider._normalize_colour_keys(config.grainfather_custom_stream_urls)
        self.temp_unit = GrainfatherCustomStreamCloudProvider._get_temp_unit(config)
        self.str_name = "Grainfather Custom URL"
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
        #logger.info("start called")
        if self.enabled():
            pass

    async def update(self):
        # 
        log_period = self.period//self.rate # older than this = stale data, ensure this is an integer of seconds
        if self.averaging_period > log_period:
            raise Exception(f"Error in config for {self.str_name} provider: Invalid combination of log ({log_period}) & averaging ({self.averaging_period}) periods")
        try:
            for colour in self.col_dest:
                #self.update_in_progress = True
                status, wait_for = [None, None] 
                #logger.debug(f"try to get {colour}, av_period={self.averaging_period}, log_period={log_period}")
                tempF, SG = self.data_archive.get_data(colour, av_period=self.averaging_period, log_period=log_period)#, averaging=True)
                if tempF and SG:
                    #logger.info(f"Timer testing colour:{colour} tempF:{tempF}, SG:{SG}")
                    tilt_status = TiltStatus(colour, tempF, SG, self.bridge_config)
                    #logger.info(f"{self._get_temp_value(tilt_status)}{self.temp_unit} SG:{tilt_status.gravity}")
                    status, wait_for = await self.async_update(tilt_status)
                else:
                    logger.info(f"{colour} has no data")
                #self.update_in_progress = False
                return [status, wait_for] # either values or [None, None]
                
        except requests.ConnectionError:
            logger.info('requests Connection error. todo: we need a task that periodically ensures WLAN connection is working')
        except Exception as e:
            logger.error(f"exception in provider.update: {e}")
        finally:
            return [status, wait_for] # either values or [None, None]
    
    def attach_archive(self, data_archive: TiltHistory):
        # keep a referene to the data queue, this is added after the object is created
        self.data_archive = data_archive
    

    async def async_update(self, tilt_status: TiltStatus):
        
        if tilt_status.colour in self.col_dest.keys():
            url = self.col_dest[tilt_status.colour]
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            payload = self._get_payload(tilt_status)
            #logger.info("send payload: {}".format(json.dumps(payload)))
            gc.collect()
            start = gc.mem_free() #don't call if in a thread?
            #todo handle timeout error
            try:
                response = await requests.post(url, headers=headers, data=json.dumps(payload), timeout=7)
                # do some logging
                status, wait_for = await self.process_response(response, start)
                #logger.debug(f"process response returned: {status} {wait_for}")
                time_spent = time.ticks_diff(time.ticks_ms(), start_time)
                # send back the status code & retry after if present
                return [status, wait_for]
            except requests.ConnectionError:
                logger.error("ConnectionError: uploading Grainfather Custom device")
                raise Exception('requests ConnectionError')
            except requests.TimeoutError:
                logger.warning("TimeoutError: uploading Grainfather Custom device")
                #logger.info(f'requests Timeout error.')
                response = None
                raise Exception("requests Timeout error.") #requests.TimeoutError
                #todo: handle this in the calling function

    def enabled(self):
        return True if self.col_dest else False

    async def process_response(self, response, start_bytes):
        # check result code
        logger.debug(f"process response {response.status_code}")
        retry_in = None
        if response.status_code == 429:
            retry_in = int(response.headers.get('retry-after')) # else None
            logger.info(f"URL response:{response.status_code}, reason:{response.reason}, size:{start_bytes - gc.mem_free()}bytes, wait:{retry_in} ")#test:{response.text}")
            # todo: update timer 
        elif response.status_code == 200:
            # malformed data?
            logger.warning("URL response:{}, reason:{}, size:{}bytes, text:{}".format(response.status_code, response.reason, start_bytes - gc.mem_free() ))#, response.text))
        elif response.status_code == 201:
            # all good
            logger.debug("URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start_bytes - gc.mem_free()))#, response.text))
        else:
            # some other error
            logger.warning("URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start_bytes - gc.mem_free()))
        await asyncio.sleep_ms(0)
        return [response.status_code, retry_in]

    def _get_payload(self, tilt_status: TiltStatus):
        # GF payload data format
        return {
            "specific_gravity": tilt_status.gravity,
            "temperature": self._get_temp_value(tilt_status),
            "unit": self.temp_unit
        } 
        
    def _get_temp_value(self, tilt_status: TiltStatus):
        if self.temp_unit == "fahrenheit":
            return tilt_status.temp_fahrenheit
        else:
            return tilt_status.temp_celsius

    # takes dict of colour->urls
    # returns dict with all colours in lowercase letters for easier matching later
    @staticmethod
    def _normalize_colour_keys(col_dest):
        normalized_colours = dict()
        if col_dest is not None:
            for colour in col_dest:
                normalized_colours[colour.lower()] = col_dest[colour]
        return normalized_colours

    @staticmethod
    def _get_temp_unit(config: BridgeConfig):
        temp_unit = config.grainfather_temp_unit.upper()
        if temp_unit == "C":
            return "celsius"
        elif temp_unit == "F":
            return "fahrenheit"
        raise ValueError("Grainfather temp unit must be F or C")
