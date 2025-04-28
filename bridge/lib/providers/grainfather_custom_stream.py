# Payload docs are found by clicking the "info" button next to a fermenation device on grainfather.com
# {
#     "specific_gravity": 1.034, //this must be a numeric value
#     "temperature": 18, //this must be numeric
#     "unit": "celsius" || "fahrenheit" //supply the unit that matches the temperature you are sending
# }

#import time
import logging
from models import TiltStatus
from models import TiltHistory
from abstractions import BridgeProviderBase
from configuration import BridgeConfig
import asyncio
#import async_urequests as requests
import aiohttp
import json
import gc
from machine import Timer
import network
#from . import grainfather_post

logger = logging.getLogger('GFcstm_pvdr')
logger.info("Startup")

class GrainfatherCustomStreamCloudProvider(BridgeProviderBase):

    def __init__(self, config: BridgeConfig):
        self.col_dest = GrainfatherCustomStreamCloudProvider._normalise_colour_keys(config.grainfather_custom_stream_urls)
        #self.temp_unit = GrainfatherCustomStreamCloudProvider._get_temp_unit(config)
        self.temp_unit = config.get_temp_unit("grainfather_temp_unit", name=True)
        self.str_name = "Grainfather Custom URL"
        self.rate = 1
        self.period = (60 * 15)  # 15 minutes
        self.upload_timer = None
        self.averaging_period = config.get_averaging_period("grainfather_averaging_period")
        self.bridge_config = config
        self.sta_if=network.WLAN(network.STA_IF)

    def __str__(self):
        return self.str_name

    def start(self):
        # todo: start is called from main script, but no longer does anything here
        #logger.info("start called")
        if self.enabled():
            pass

    async def update(self):
        # print("in GF custom")
        log_period = self.period//self.rate # older than this = stale data, ensure this is an integer of seconds
        if self.averaging_period > log_period:
            raise Exception(f"Error in config for {self.str_name} provider: Invalid combination of log ({log_period}) & averaging ({self.averaging_period}) periods")
        res = [False, False]
        try:
            for colour in self.col_dest:
                #self.update_in_progress = True
                #logger.debug(f"try to get {colour}, av_period={self.averaging_period}, log_period={log_period}")
                tempF, SG = self.data_archive.get_data(colour, av_period=self.averaging_period, log_period=log_period)
                if tempF and SG:
                    #logger.info(f"Timer testing colour:{colour} tempF:{tempF}, SG:{SG}")
                    tilt_status = TiltStatus(colour, tempF, SG, self.bridge_config)
                    #res = await self.async_update(tilt_status)
                    
                    url = self.col_dest[tilt_status.colour]
                    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                    payload = self._get_payload(tilt_status)
                    #logger.debug("send payload: {}".format(json.dumps(payload)))
                    gc.collect()
                    #start = gc.mem_free()
                    if self.sta_if.status() == 3: #connected:
                        # print("async_update2")
                        res = await self.grainfather_post(url, payload)
                        #send as a dict
                    else:
                        print("not connected, expect a long wait before an error")
                        #TODO raise an eror/warning here?
                        #res = asyncio.run(post(url, data))
                        
                else:
                    logger.info(f"{colour} has no data")
                #self.update_in_progress = False
                # print("about to return")
                #return res # either values or [None, None]
                '''except requests.ConnectionError:
                        res = [False, False]
                        logger.error(f"ConnectionError: uploading {self.str_name} device")
                        raise Exception('requests ConnectionError')
                except requests.TimeoutError:
                    logger.warning(f"TimeoutError: uploading {self.str_name} device")
                    #logger.info(f'requests Timeout error.')
                    #response = None
                    raise Exception("requests Timeout error.") #requests.TimeoutError'''
        except Exception as e:
            raise e
        finally:
            # return the result
            if res[0]:
                logger.debug(f"{self.str_name} updated for {colour} Tilt")
            return res
    
    def attach_archive(self, data_archive: TiltHistory):
        # keep a referene to the data queue, this is added after the object is created
        self.data_archive = data_archive
    
    def enabled(self):
        return True if self.col_dest else False

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
    def _normalise_colour_keys(col_dest):
        normalised_colours = dict()
        if col_dest is not None:
            for colour in col_dest:
                normalised_colours[colour.lower()] = col_dest[colour]
        return normalised_colours

    async def grainfather_post(self, url, data):
        #def post(url, data):
        ''' pass in a url & json payload
            process response and returns [status_code, retry_secs]
            
        '''
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        #async with aiohttp.ClientSession("http://httpbin.org") as session:
        try:
            #20230313 see same date in providers.__init__
            # timeout seems to work, but I don't full understand the whole aiohttp package
            #async with aiohttp.ClientSession(headers=headers) as session:
            async with aiohttp.ClientSession(headers=headers, timeout=7) as session:
                #start = time.ticks_ms()
                async with session.post(url, json=data) as resp:
                    result, interp = [None, None], None
                    # today try:
                    interp, rpost, rheaders, rstatus = "", "", "", 0
                    if resp.status == 201:
                        result = [201, None]
                        #interp = None
                    elif resp.status == 429:
                        result = [False, int(resp.headers['retry-after'])]
                        logger.warning(f"Too many requests, retry in {resp.headers['retry-after']}secs") #{resp.headers['retry-after'])}
                        #interp = None
                    elif resp.status == 405:
                        interp = "405: Method not allowed. JSON data is incorrectly formatted, either incorrect keys or data values"
                    elif resp.status == 422:
                        interp = "422: there is an issue with the JSON payload, possibly incorrect keys or data values"
                        # Grainfather website says this will be response if there is an issue with the JSON payload, but I cannot trigger it
                    elif resp.status == 404:
                        interp = "404: Page not found. The url seems to be incorrect, check the /xxxx-yyyy/ part of the url"
                        # ie sending to https://community.grainfather.com/iot/xxxbans-yyynabe/tilt should be bans-nabe
                    elif resp.status == 400:
                        interp = "400: Token to device mismatch. The url seems to be incorrect, change the end of the url from custom to tilt or vice versa"
                        # ie sending to https://community.grainfather.com/iot/bans-nabe/custom should end in /tilt
                    elif resp.status == 200:
                        interp = "200: Data received but not updated. Possibly an error on Grainfather website"
                    else:
                        interp = f"{resp.status}: This error is unhandled"
                    if interp:
                        logger.error(interp)
                        # print(interp)
                        #20250313 trap asyncio.TimeoutError
        except asyncio.TimeoutError as e:
            logger.error(f"TimeoutError: data was not uploaded, wait for next update interval")
            #result = [False, 10]
        except Exception as e:
            logger.error(f"{type(e)}: {e}")
            # print(f"{type(e)}: {e}")
            raise e
        finally:
            return result
