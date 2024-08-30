''' changed time.time() to time.ticks_ms()
    use time.ticks_diff rather than subtract time
    this should give better resolution, ie catch the timer in ms rather than seconds
    however will always miss the event, by up to 1 data reception interval (typically 1 second?)
    
    alternate approach would be to have a timer event in this class
    the main code then awaits any of the provider timer events then upload the most recent data point(s)
    in that case the interval should remain more constant, but would need to check a timestamp o the data to ensure is within say 1/3 of rate
'''
import time


class RateLimitedException(Exception):
    pass


class DeviceRateLimiter:
    def __init__(self, rate=1, period=1):
        self.default_rate = rate
        self.default_period = period
        self.device_limiters = dict()

    def approve(self, device_id):
        if device_id not in self.device_limiters:
            # No limiter for this device yet
            self.device_limiters[device_id] = self._get_new_limiter()
        # Check if this color is too frequent
        limiter = self.device_limiters[device_id]
        limiter.approve()

    def _get_new_limiter(self):
        return RateLimiter(self.default_rate, self.default_period)


class RateLimiter:
    def __init__(self, rate=1, period=1):
        self.rate = rate 
        self.period = period * 1000 # convert from second to ms
        self.allowance = rate
        self.last_check = time.ticks_ms() #time.time()

    def approve(self):
        current = time.ticks_ms() # time.time()
        time_passed = time.ticks_diff(current, self.last_check) # current - self.last_check
        self.last_check = current
        self.allowance = self.allowance + time_passed * (self.rate / self.period)
        if self.allowance > self.rate:
            self.allowance = self.rate
            # we have missed the event by ??ms
        if self.allowance < 1:
            raise RateLimitedException() # - (self.rate / self.period)
        # allow to go early by up to 1 second?
        else:
            self.allowance = self.allowance - 1 # allow, or at least don't return an error
