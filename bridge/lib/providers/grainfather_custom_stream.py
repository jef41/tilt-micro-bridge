# Payload docs are found by clicking the "info" button next to a fermenation device on grainfather.com
# {
#     "specific_gravity": 1.034, //this must be a numeric value
#     "temperature": 18, //this must be numeric
#     "unit": "celsius" || "fahrenheit" //supply the unit that matches the temperature you are sending
# }

import time
#import logging
from models import TiltStatus
#from abstractions import CloudProviderBase
from configuration import BridgeConfig
from rate_limiter import DeviceRateLimiter
#from interface import implements
import asyncio
import async_urequests as requests
#import requests
#from async_urequests import urequests as requests #synchronous & timeouts
#import async_urequests as requests
#import urequests_ff as requests
import json
#from collections import OrderedDict
import gc # for development only
from rate_limiter import RateLimitedException


#dbg_logger = logging.getLogger("main.GFcustomProvider")
#logger = logging.getLogger('GFcustomProvider')
#logger.setLevel(logging.DEBUG)

#class GrainfatherCustomStreamCloudProvider(implements(CloudProviderBase)):
class GrainfatherCustomStreamCloudProvider():

    def __init__(self, config: BridgeConfig):
        self.colour_urls = GrainfatherCustomStreamCloudProvider._normalize_colour_keys(config.grainfather_custom_stream_urls)
        self.temp_unit = GrainfatherCustomStreamCloudProvider._get_temp_unit(config)
        self.str_name = "Grainfather Custom URL"
        self.rate_limiter = DeviceRateLimiter(rate=1, period=(60 * 15))  # 15 minutes
        self.update_due = False
        #logger.info("test provider")

    def __str__(self):
        return self.str_name

    def start(self):
        # initialise a timer and IRQ here to change update_due flag
        pass

    def update(self, tilt_status: TiltStatus):
        asyncio.run(self.a_update(tilt_status))
        #self.a_update(tilt_status)
        #self.synchronous_update(tilt_status)
        '''try:
            asyncio.run(self.a_update(tilt_status))
            #await self.a_update(tilt_status)
            #asyncio.create_task(self.a_update(tilt_status))
        except Exception as e:
            print("async update error:{}".format(e))'''

    #def async update(self, tilt_status: TiltStatus):
    async def a_update(self, tilt_status: TiltStatus):
        start_time = time.ticks_ms()
        #print("debug: async GF Custom provider called")#, with\n{}").format(dir(tilt_status)))
        # Skip if this colour doesn't have a grainfather URL assigned
        #print(f"tilt_status.colour {tilt_status.colour} is in self.colour_urls.keys()? {self.colour_urls.keys()}")
        #if tilt_status.colour not in self.colour_urls.keys():
        #    print("not in")
        #    #return
        #else:
        if tilt_status.colour in self.colour_urls.keys():
            url = self.colour_urls[tilt_status.colour]
            self.rate_limiter.approve(tilt_status.colour)
            #try:
            #    self.rate_limiter.approve(tilt_status.colour)
            #except RateLimitedException:
            #    # nothing to worry about, just called this too many times (locally)
            #    #raise RateLimitedException()
            #    #print("Skipping update due to rate limiting for GC_custom for colour {}".format(tilt_status.colour))
            #    raise RateLimitedException()
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            payload = self._get_payload(tilt_status)
            #print("send payload: {}".format(json.dumps(payload)))
            #print("send payload: {}".format(json.dumps(payload)))
            start = gc.mem_free() #don't call if in a thread?
            #try:
            # todo temporarily block rate_limiter so we don't repeat requests while one is pending?
            #  using await below returns nothing
            #response = await requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
            #todo handle timeout error
            try:
                response = await requests.post(url, headers=headers, data=json.dumps(payload), timeout=7)
                #response = asyncio.create_task(requests.post(url, headers=headers, data=json.dumps(payload), timeout=0.1))
                #print("custom response is:{} bytes".format(start - gc.mem_free()))
                #await response
                print("Custom URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start - gc.mem_free()))#, response.text))
                retry_in = int(response.headers.get('retry-after')) if response.status_code == 429 else None
                #print("Retry in:{}".format(retry)) if retry else print("no retry value, so data updated")
                time_spent = time.ticks_diff(time.ticks_ms(), start_time)
                #self._adjust_timing(response.status_code, retry_in, time_spent, tilt_status)
                response.close()
                response = None # make available for gc
            except requests.ConnectionError:
                raise Exception('requests Connection error.')
            except requests.TimeoutError:
                #print(f'requests Timeout error.')
                response = None
                raise Exception("requests Timeout error.") #requests.TimeoutError
                #todo: handle this in the calling function
            finally:  # Usual way to do cleanup 
                pass
        
        #http_return(int(response.status_code), response.headers)
        # todo: handle retry after (if not none),
        # todo: adapt requests to not read content line 223 in async_urequests
        #asyncio.run(requests("POST", url, json=payload))
        #response = await requests.post(url, json=payload, headers=headers)    
        #except Exception as e:
        #print(f"GF Custom response.post error: {e}")
        #print("send payload:\n{}".format(payload))
        #response = requests.post(url, headers=headers, data=payload)
        # result.raise_for_status()
        #finally:
        # updarte rate limiter according to response
        # if 201 then retore to config vcalue
        # if 429 set to 1 minute?
        # if config round then wait for 0,15,30,45 mins of the hour?

    def synchronous_update(self, tilt_status: TiltStatus):
        #print("debug: synchronous GF Custom provider called")#, with\n{}").format(dir(tilt_status)))
        # Skip if this colour doesn't have a grainfather URL assigned
        if tilt_status.colour not in self.colour_urls.keys():
            return
        url = self.colour_urls[tilt_status.colour]
        self.rate_limiter.approve(tilt_status.colour)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        payload = self._get_payload(tilt_status)
        print("send payload: {}".format(json.dumps(payload)))
        start = gc.mem_free() #don't call if in a thread?

        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        #print("custom response is:{} bytes".format(start - gc.mem_free()))
        print("Custom URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start - gc.mem_free()))#, response.text))
        #asyncio.run(requests("POST", url, json=payload))
        response.close()
        response = None # make available for gc

    def enabled(self):
        return True if self.colour_urls else False

    def _adjust_timing(self, status, retry_secs: int, time_spent, tilt_status):
        '''match status: '''
        if status == 201:
            #self.rate_limiter.device_limiters[tilt_status.colour].period = int(600)
            time_spent = time_spent / 1000
            print("default_period:{} time_spent:{}".format( self.rate_limiter.default_period, time_spent))
            # subtracting time spent did not work
            self.rate_limiter.device_limiters[tilt_status.colour].period = (self.rate_limiter.default_period + time_spent)
            # below makes 1 min fast after 19 iterations
            #self.rate_limiter.device_limiters[tilt_status.colour].period = (self.rate_limiter.default_period - self.rate_limiter.device_limiters[tilt_status.colour].overrun)
            print("rate set to :{}".format(self.rate_limiter.device_limiters[tilt_status.colour].period))
            #all ok, updated, try again in 15 mins - time it took to get last response
            # % 15 here & if config.roundup then adjust to next interval
        elif status == 429:
            #retry = response.headers.get('retry-after')
            #self.rate_limiter.period = retry_secs
            #print(dir(self.rate_limiter.device_limiters.items)) #device_limiters[tilt_status.colour])#.period = retry_secs
            #for i in self.rate_limiter.device_limiters:
            #    print(f"{i}")
            #print(dir(self.rate_limiter.device_limiters[tilt_status.colour]))
            self.rate_limiter.device_limiters[tilt_status.colour].period = int(retry_secs)
            #if retry:
            #    print("Retry in:{}".format(retry))
            #else:
            #    print("no retry value, so data updated")
            last_t = time.localtime(self.rate_limiter.device_limiters[tilt_status.colour].last_check)
            next_t = time.localtime(time.time() + retry_secs)
            print("last_check:\t{0:02d}:{1:02d}:{2:02d}, retry at {3:02d}:{4:02d}:{5:02d}".format(last_t[3],last_t[4],last_t[5], next_t[3], next_t[4], next_t[5]))
            #str(self.rate_limiter(tilt_status.colour).last_check))
            # todo look for retry & update rate limiter
        else:
            pass
            # something else wrong, log a message
            #return "Something's wrong with the internet"

    def _get_payload(self, tilt_status: TiltStatus):
        # GF requires the JSON to to ordered correctly TODO - maybe ordiered dict not required, but this did work!
        '''payld = OrderedDict([
            ("specific_gravity", tilt_status.gravity),
             ("temperature", self._get_temp_value(tilt_status)),
             ("unit", self.temp_unit)
        ])return payld'''
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
    def _get_temp_unit(config: PitchConfig):
        temp_unit = config.grainfather_temp_unit.upper()
        if temp_unit == "C":
            return "celsius"
        elif temp_unit == "F":
            return "fahrenheit"

        raise ValueError("Grainfather temp unit must be F or C")

