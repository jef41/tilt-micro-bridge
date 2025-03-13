''' convert & return values from a Tilt device (or TiltHistory) 
'''
from configuration import BridgeConfig
from .json_serialize import JsonSerialize
#import time

class TiltStatus(JsonSerialize):
    # class to process/format Tilt data from beacon or in/out of data store
    # apply_calibration=False means store the uncalibrated sample, this should be done when saving data
    def __init__(self, colour, uncal_temp_fahrenheit, uncal_SG, config: BridgeConfig, apply_calibration=True):
        self.config = config
        self.colour = colour
        self.name = config.get_brew_name(colour)
        self.hd = uncal_SG > 2  # Tilt Pro
        # print(f"***  self.hd: {self.hd}, {uncal_SG:.3f}")
        # With Tilt Pro values have more precision, which has to be adjusted
        if self.hd:
            uncal_SG /= 10
        uncal_temp_fahrenheit /= 10
        #print(f"***  uncal: {uncal_SG}")
        if apply_calibration:
            # apply calibration, if present
            try:
                self.temp_fahrenheit = round(
                    TiltStatus.apply_cal(
                        uncal_temp_fahrenheit, 
                        config.get_temp_offsets(self.colour)
                    ), 
                    2
                )
            except Exception as e:
                raise type(e)(f"TiltStatus: Temperature calibration is invalid, ignoring: {e}: ") from e
                #TODO create logger here?
                self.temp_fahrenheit = uncal_temp_fahrenheit
            #print(f"***  cal vals {colour} {vals}")
            self.gravity = TiltStatus.apply_cal(uncal_SG, config.get_gravity_offsets(self.colour))
            self.gravity = round(self.gravity, 4) if self.hd else round(self.gravity, 3)
            #print(f"***    cal: {self.gravity} from uncal: {uncal_SG}")
        else:
            self.temp_fahrenheit = uncal_temp_fahrenheit
            self.gravity = uncal_SG
        self.temp_celsius = TiltStatus.get_celsius(self.temp_fahrenheit)
        self.original_gravity = config.get_original_gravity(colour)
        self.degrees_plato = TiltStatus.get_degrees_plato(self.gravity)
        self.alcohol_by_volume = TiltStatus.get_alcohol_by_volume(self.original_gravity, self.gravity)
        self.apparent_attenuation = TiltStatus.get_apparent_attenuation(self.original_gravity, self.gravity)
        self.temp_valid = (config.temp_range_min < self.temp_fahrenheit and self.temp_fahrenheit < config.temp_range_max)
        self.gravity_valid = (config.gravity_range_min < self.gravity and self.gravity < config.gravity_range_max)

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
        #alcohol_by_volume = (original_gravity - current_gravity) * 131.25
        alcohol_by_volume = (76.08 * (original_gravity - current_gravity) / (1.775 - original_gravity)) * (current_gravity / 0.794)
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
        #TODO: not used?
        pass

    @staticmethod
    def apply_cal(current_raw, cal_vals):
        if cal_vals is None: # config.get_gravity_offsets(colour) is None:
            cal_result = current_raw
        else:
            cal_result = TiltStatus.linear_interpolate(current_raw, cal_vals)
        return cal_result
        
    def linear_interpolate(xin,cal_vals):
        ''' takes input of an x value & list of x,y values
        returns interpolated x
        SG/temp passed here should be e.g. 1.035 not 1035
        '''
        #same approach as Tilt App, append & prepend extreme values
        if cal_vals:
            cal_vals = [ [-0.001,-0.001], [10**5,10**5] ] + cal_vals
            cal_vals.sort(key=lambda x: x[1]) # sort by 2nd value in list
            #print(f"{cal_vals}")
        for x,y in cal_vals:
            if x == xin:  # <- exact match
                return y
            if x > xin:   # px<xin<x <- assuming there was already a px
                return py + (y - py) * (xin - px) / (x - px)  # noqa: F821
            px = x
            py = y
