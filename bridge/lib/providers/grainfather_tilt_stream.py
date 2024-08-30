# GF always expects jsut an SG & Temp in Farenheit
# will display on GF website in user preferred units configured in preferences on that platform
# {
#     "SG": 1.034, //this must be a numeric value
#     "Temp: 70, //this must be numeric
# }

from models import TiltStatus
#from abstractions import CloudProviderBase
from configuration import BridgeConfig
from rate_limiter import DeviceRateLimiter
#from interface import implements
#import requests
#or 
import asyncio
import async_urequests as requests
import json
import gc # for development only


#class GrainfatherTiltStreamCloudProvider(implements(CloudProviderBase)):
class GrainfatherTiltStreamCloudProvider():

    def __init__(self, config: BridgeConfig):
        self.colour_urls = GrainfatherTiltStreamCloudProvider._normalize_colour_keys(config.grainfather_tilt_stream_urls)
        self.temp_unit = GrainfatherTiltStreamCloudProvider._get_temp_unit(config)
        self.str_name = "Grainfather Tilt URL"
        self.rate_limiter = DeviceRateLimiter(rate=1, period=(60 * 15))  # 15 minutes
        self.update_due = False

    def __str__(self):
        return self.str_name

    def start(self):
        # initialise a timer and IRQ here to change update_due flag
        pass

    def update(self, tilt_status: TiltStatus):
        asyncio.run(self.async_update(tilt_status))
        #self.synchronous_update(tilt_status)

    def synchronous_update(self, tilt_status: TiltStatus):
        ''' use
            import requests
            #import asyncio
            #import async_urequests as requests
        '''
        #print("debug: GF Tilt provider called")#, with\n{}").format(dir(tilt_status)))
        # Skip if this colour doesn't have a grainfather URL assigned
        if tilt_status.colour not in self.colour_urls.keys():
            return
        url = self.colour_urls[tilt_status.colour]
        self.rate_limiter.approve(tilt_status.colour)
        #headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        payload = self._get_payload(tilt_status)
        print("send payload: {}".format(json.dumps(payload)))
        start = gc.mem_free()
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=8)
        #print("tilt response is:{} bytes".format(start - gc.mem_free()))
        #print("send payload:\n{}".format(payload))
        #response = requests.post(url, headers=headers, data=payload)
        # result.raise_for_status()
        print("GF Tilt, response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start - gc.mem_free()))#, response.text))
        response.close()
        response = None # make available for gc

    #async
    def async_update(self, tilt_status: TiltStatus):
        ''' use
            #import requests
            import asyncio
            import async_urequests as requests
        '''
        #print("debug: sync GF Tilt provider called")#, with\n{}").format(dir(tilt_status)))
        # Skip if this colour doesn't have a grainfather URL assigned
        if tilt_status.colour not in self.colour_urls.keys():
            return
        url = self.colour_urls[tilt_status.colour]
        self.rate_limiter.approve(tilt_status.colour)
        
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        payload = self._get_payload(tilt_status)
        print("send payload: {}".format(json.dumps(payload)))
        start = gc.mem_free() #don't call if in a thread?
        response = await requests.post(url, headers=headers, data=json.dumps(payload), timeout=5)
        print("Custom URL response:{}, reason:{}, size:{}bytes".format(response.status_code, response.reason, start - gc.mem_free()))#, response.text))

        # update rate limiter according to response
        # if 201 then restore to config value
        # if 429 set to 1 minute?
        # if config option set to round then wait for 0,15,30,45 mins of the hour?
        response.close()
        response = None # make available for gc

    def enabled(self):
        return True if self.colour_urls else False
    
    def _get_payload(self, tilt_status: TiltStatus):
        '''return {
            "specific_gravity": tilt_status.gravity,
            "temperature": self._get_temp_value(tilt_status),
            "unit": self.temp_unit
        } '''
        return {
            "SG": tilt_status.gravity,
            "Temp": self._get_temp_value(tilt_status)
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
        ''' Grainfather is expecting Farenheit & will convert/display in user preferred units'''
        return "fahrenheit"




