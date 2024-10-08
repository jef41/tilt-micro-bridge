from configuration import BridgeConfig
from .json_serialize import JsonSerialize
#from machine import RTC
import time


class TiltStatus(JsonSerialize):

    def __init__(self, colour, temp_fahrenheit, current_gravity, config: BridgeConfig):
        #self.timestamp = datetime.datetime.now()
        # TODO get net connection, get correct timestamp
        #rtc = RTC()
        #self.timestamp = TiltStatus.get_timestamp()
        self.colour = colour
        self.name = config.get_brew_name(colour)
        self.hd = current_gravity > 2  # Tilt Pro?

        # With Tilt Pro values have more precision, which has to be adjusted
        if self.hd:
            current_gravity /= 10
            temp_fahrenheit /= 10

        self.temp_fahrenheit = temp_fahrenheit + config.get_temp_offset(colour)
        self.temp_celsius = TiltStatus.get_celsius(self.temp_fahrenheit)
        self.original_gravity = config.get_original_gravity(colour)
        self.gravity = current_gravity + config.get_gravity_offset(colour)
        self.degrees_plato = TiltStatus.get_degrees_plato(self.gravity)
        self.alcohol_by_volume = TiltStatus.get_alcohol_by_volume(self.original_gravity, self.gravity)
        self.apparent_attenuation = TiltStatus.get_apparent_attenuation(self.original_gravity, self.gravity)
        self.temp_valid = (config.temp_range_min < self.temp_fahrenheit and self.temp_fahrenheit < config.temp_range_max)
        self.gravity_valid = (config.gravity_range_min < self.gravity and self.gravity < config.gravity_range_max)
        #print("debug: tilt status initialised")

    #@staticmethod
    #def get_timestamp():
    #    #year, month, day, hour, mins, secs, weekday, yearday = time.localtime()
    #    # Print a date - YYYY-MM-DD
    #    #return str("{:02d}:{:02d}:{:02d}".format(hour, mins, secs))
    #    return time.time() # epoch, can be relative, but we should have ntp

    @staticmethod
    def get_celsius(temp_fahrenheit):
        return round((temp_fahrenheit - 32) * 5.0/9.0, 1)

    @staticmethod
    def get_degrees_plato(gravity):
        return round(1111.14 * gravity - 630.272 * gravity ** 2 + 135.997 * gravity ** 3 - 616.868, 1)

    @staticmethod
    def get_alcohol_by_volume(original_gravity, current_gravity):
        if original_gravity is None:
            return 0
        alcohol_by_volume = (original_gravity - current_gravity) * 131.25
        return round(alcohol_by_volume, 2)

    @staticmethod
    def get_apparent_attenuation(original_gravity, current_gravity):
        if original_gravity is None:
            return 0
        aa = ((original_gravity - current_gravity) / original_gravity) * 2 * 1000
        return round(aa, 2)

    @staticmethod
    def get_gravity_points(gravity):
        """Converts gravity reading like 1.035 to just 35"""
