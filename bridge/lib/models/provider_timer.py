''' class to hold a list of timers for each provider
    and to handle general timer functions init, reinit, adjust
    callback sets a provider flag
    can be initialised with a non-default value or reinitialised with a different value
    in either case on next interrupt timer will revert to default value
'''
import asyncio
from machine import Timer
import logging

logger = logging.getLogger("PvdrTimer")

class UploadTimers():
    def __init__(self):
        self.timer_list = dict()
    
    def add(self, provider, period, adjust=None):
        adjust = None if adjust == 0 else adjust # ensure we don't set invalid adjustment period
        self.timer_list[provider] = self._get_new_timer(period, adjust)
    
    def _get_new_timer(self, period, adjust):
        return ProviderTimer(period, adjust)
    
    def upload_is_due(self, provider):
        # is upload flag set?
        result = False
        if self.timer_list[provider].upload_due.is_set():
            result = True
            #self.timer_list[provider].upload_due.clear()
            self.timer_list[provider].upload_due.clear()
            # immediately clear this flag once read, it may take a while for update method to return
            # todo implement a timeout here, so if it fiales after 10 secs, then retries rather than wait log interval?
        return result
    
    def clear(self, provider):
        # clear the flag
        self.timer_list[provider].clear()
    
    def stop(self, provider):
        # stop the timer
        self.timer_list[provider].stop()
    
    def adjust(self, provider, period_new):
        # change the timer period
        self.timer_list[provider].reinit(period_new*1000)
        self.timer_list[provider].adjusted = True
        logger.debug(f"{provider} timer adjusted to: {period_new}secs")
        self.timer_list[provider].upload_due.clear() # ensure the flag is reset
        #oneshot timer object remains once it has expired

class ProviderTimer():
    def __init__(self, default_period, adjust=None):
        # the first upload may be a different interval ie after averaging period (5mins) not logging period (15mins)
        # in which case call with default_period=900, adjust=300
        self.upload_due = asyncio.Event()
        #self.upload_due.clear()
        self.default_period = default_period*1000 if default_period else 1000 # default to 1 second if averaging set to 0
        self.adjusted = False
        if adjust is not None:
            adjust = adjust*1000
            self.adjusted = True
        self.reinit(self.default_period if adjust is None else adjust)
        #self.upload_timer = Timer(period=self.default_period, mode=Timer.PERIODIC, callback=self.provider_callback)
        logger.debug(f"timer created with period {self.default_period if adjust is None else adjust}")

    def provider_callback(self, timer):
        # set the thread safe flag
        self.upload_due.set()
        if self.adjusted:
            # reset to the default
            self.reinit(self.default_period)
            logger.debug("timer reset to default")
    
    def stop(self):
        self.upload_timer.deinit()
    
    def clear(self):
        self.upload_due.clear()
    
    def reinit(self, ms_period):
        #(re)initialise a timer
        try:
            self.upload_timer.deinit()
        except AttributeError:
            # timer does not exist yet, carry on
            pass
        self.upload_timer = Timer(period=ms_period, mode=Timer.PERIODIC, callback=self.provider_callback)
        if ms_period == self.default_period:
            self.adjusted = False
        else:
            self.adjusted = True
            