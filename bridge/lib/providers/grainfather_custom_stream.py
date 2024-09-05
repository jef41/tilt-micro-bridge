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
#from abstractions import CloudProviderBase
from configuration import BridgeConfig
#from rate_limiter import DeviceRateLimiter
import asyncio
import async_urequests as requests
import json
import gc # for development only
#from rate_limiter import RateLimitedException
from machine import Timer


logger = logging.getLogger('GFcstm_pvdr')
logger.info("Startup")

#class GrainfatherCustomStreamCloudProvider(implements(CloudProviderBase)):
class GrainfatherCustomStreamCloudProvider():

    def __init__(self, config: BridgeConfig):
        self.colour_urls = GrainfatherCustomStreamCloudProvider._normalize_colour_keys(config.grainfather_custom_stream_urls)
        self.temp_unit = GrainfatherCustomStreamCloudProvider._get_temp_unit(config)
        self.str_name = "Grainfather Custom URL"
        #self.rate_limiter = DeviceRateLimiter(rate=1, period=(60 * 15))  # 15 minutes
        self.rate = 1
        self.period = (60 * 15)  # 15 minutes
        #self.update_due = False
        self.upload_timer = None
        try:
            self.averaging_period = config.grainfather_averaging_period
        except AttributeError:
            self.averaging_period = config.averaging_period
        self.bridge_config = config
        #self.start()
        #self.upload_due = asyncio.Event() # ThreadSafeFlag()
        #logger.info("test provider")

    def __str__(self):
        return self.str_name

    def start(self):
        # todo: start is called from main script, but no longer does anything here
        #logger.info("start called")
        if self.enabled():
            #self.upload_timer = Timer(period=((self.period//self.rate)*1000), mode=Timer.PERIODIC, callback=self.update_test)
            #self.upload_timer = Timer(period=((self.period//self.rate)*1000), mode=Timer.PERIODIC, callback=self.provider_callback)
            #self.upload_timer = Timer(period=900, mode=Timer.PERIODIC, callback=self.test)
            #upload_timer.init(period=900, mode=Timer.PERIODIC, callback=self.test)
            #logger.info(f"{self.str_name} provider timer started")
            pass

    
    def provider_callback(self, timer):
        # set the thread safe flag
        self.upload_due.set()
    
    #def update_test(self, t):
    async def update_test(self):
        # for colour in self.colour_urls
        #averagering_period = config.averaging_period
        log_period = self.period/self.rate # older than this = stale data
        if self.averaging_period > log_period:
            raise Exception(f"Error in config for {self.str_name} provider: Invalid combination of log ({log_period}) & averaging ({self.averaging_period}) periods")
        try:
            for colour in self.colour_urls:
                tempF, SG = self.data_archive.get_data(colour, av_period=self.averaging_period, log_period=log_period)#, averaging=True)
                if tempF and SG:
                    #logger.info(f"Timer testing colour:{colour} tempF:{tempF}, SG:{SG}")
                    tilt_status = TiltStatus(colour, tempF, SG, self.bridge_config)
                    #logger.info(f"{self._get_temp_value(tilt_status)}{self.temp_unit} SG:{tilt_status.gravity}")
                    asyncio.run(self.async_update(tilt_status))
                else:
                    #logger.info(f"{colour} has no data")
                    pass
                
        except requests.ConnectionError:
            logger.info('requests Connection error. todo: we need a tassk that prtiodically ensures WLAN connection is working')
        except Exception as e:
            logger.info(f"exception in provider timer test(): {e}")
    
    def attach_archive(self, data_archive: TiltHistory):
        # keep a referene to the data queue, this is added after the object is created
        self.data_archive = data_archive
    

    async def async_update(self, tilt_status: TiltStatus):
        start_time = time.ticks_ms()
        #logger.info("debug: async GF Custom provider called")#, with\n{}").format(dir(tilt_status)))
        # Skip if this colour doesn't have a grainfather URL assigned
        #logger.info(f"tilt_status.colour {tilt_status.colour} is in self.colour_urls.keys()? {self.colour_urls.keys()}")
        #if tilt_status.colour not in self.colour_urls.keys():
        #    logger.info("not in")
        #    #return
        #else:
        if tilt_status.colour in self.colour_urls.keys():
            url = self.colour_urls[tilt_status.colour]
            #self.rate_limiter.approve(tilt_status.colour)
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            payload = self._get_payload(tilt_status)
            #logger.info("send payload: {}".format(json.dumps(payload)))
            #logger.info("send payload: {}".format(json.dumps(payload)))
            gc.collect()
            start = gc.mem_free() #don't call if in a thread?
            #todo handle timeout error
            try:
                response = await requests.post(url, headers=headers, data=json.dumps(payload), timeout=7)
                #await response
                logger.info("Custom URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start - gc.mem_free()))#, response.text))
                retry_in = int(response.headers.get('retry-after')) if response.status_code == 429 else None
                #logger.info("Retry in:{}".format(retry)) if retry else logger.info("no retry value, so data updated")
                time_spent = time.ticks_diff(time.ticks_ms(), start_time)
                #self._adjust_timing(response.status_code, retry_in, time_spent, tilt_status)
                response.close()
                response = None # make available for gc
            except requests.ConnectionError:
                raise Exception('requests Connection error.')
            except requests.TimeoutError:
                #logger.info(f'requests Timeout error.')
                response = None
                raise Exception("requests Timeout error.") #requests.TimeoutError
                #todo: handle this in the calling function
            finally:  # Usual way to do cleanup 
                pass
        
        #http_return(int(response.status_code), response.headers)
        # todo: handle retry after (if not none),
        # todo: adapt requests to not read content line 223 in async_urequests
        
        # result.raise_for_status()
        #finally:
        # updarte rate limiter according to response
        # if 201 then retore to config vcalue
        # if 429 set to 1 minute?
        # if config round then wait for 0,15,30,45 mins of the hour?


    def enabled(self):
        return True if self.colour_urls else False

    def _adjust_timing(self, status, retry_secs: int, time_spent, tilt_status):
        # todo: implement this probperly with ProviderTimer
        if status == 201:
            #self.rate_limiter.device_limiters[tilt_status.colour].period = int(600)
            time_spent = time_spent / 1000
            logger.info("default_period:{} time_spent:{}".format( self.rate_limiter.default_period, time_spent))
            # subtracting time spent did not work
            self.rate_limiter.device_limiters[tilt_status.colour].period = (self.rate_limiter.default_period + time_spent)
            # below makes 1 min fast after 19 iterations
            #self.rate_limiter.device_limiters[tilt_status.colour].period = (self.rate_limiter.default_period - self.rate_limiter.device_limiters[tilt_status.colour].overrun)
            logger.info("rate set to :{}".format(self.rate_limiter.device_limiters[tilt_status.colour].period))
            #all ok, updated, try again in 15 mins - time it took to get last response
            # % 15 here & if config.roundup then adjust to next interval
        elif status == 429:
            #retry = response.headers.get('retry-after')
            #self.rate_limiter.period = retry_secs
            #logger.info(dir(self.rate_limiter.device_limiters.items)) #device_limiters[tilt_status.colour])#.period = retry_secs
            #for i in self.rate_limiter.device_limiters:
            #    logger.info(f"{i}")
            #logger.info(dir(self.rate_limiter.device_limiters[tilt_status.colour]))
            self.rate_limiter.device_limiters[tilt_status.colour].period = int(retry_secs)
            #if retry:
            #    logger.info("Retry in:{}".format(retry))
            #else:
            #    logger.info("no retry value, so data updated")
            last_t = time.localtime(self.rate_limiter.device_limiters[tilt_status.colour].last_check)
            next_t = time.localtime(time.time() + retry_secs)
            logger.info("last_check:\t{0:02d}:{1:02d}:{2:02d}, retry at {3:02d}:{4:02d}:{5:02d}".format(last_t[3],last_t[4],last_t[5], next_t[3], next_t[4], next_t[5]))
            #str(self.rate_limiter(tilt_status.colour).last_check))
            # todo look for retry & update rate limiter
        else:
            pass
            # something else wrong, log a message
            #return "Something's wrong with the internet"

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
    def _normalize_colour_keys(colour_urls):
        normalized_colours = dict()
        if colour_urls is not None:
            for colour in colour_urls:
                normalized_colours[colour.lower()] = colour_urls[colour]

        return normalized_colours

    @staticmethod
    def _get_temp_unit(config: BridgeConfig):
        temp_unit = config.grainfather_temp_unit.upper()
        if temp_unit == "C":
            return "celsius"
        elif temp_unit == "F":
            return "fahrenheit"

        raise ValueError("Grainfather temp unit must be F or C")

'''
#for testing/debug:
def display_time():
    year, month, day, hour, mins, secs, weekday, yearday = time.localtime()
    # logger.info a date - YYYY-MM-DD
    return str("{:02d}:{:02d}:{:02d}".format(hour, mins, secs))'''