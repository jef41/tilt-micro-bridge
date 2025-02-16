'''from ..models import TiltStatus
from ..abstractions import CloudProviderBase
from ..configuration import PitchConfig
from interface import implements
import logging
import logging.handlers'''
import time
from rotating_file_handler import RotatingLogFileHandler
import logging
from models import TiltStatus
from models import TiltHistory
#from abstractions import CloudProviderBase
from configuration import BridgeConfig
import asyncio
#import async_urequests as requests
import json
#import gc # for development only
#from machine import Timer

''' TODO
    different log file per colour
'''
logger = logging.getLogger('File_pvdr')
logger.info("Startup")

class FileCloudProvider():

    def __init__(self, config: BridgeConfig):
        self.colour_urls = FileCloudProvider._normalise_colour_keys(config.log_file_tilt_colours) 
        self.temp_unit = FileCloudProvider._get_temp_unit(config)
        self.str_name = "File Logger" # .format(config.log_file_path)
        self.log_pvdr = logging.getLogger(self.str_name)
        self.rate = 1
        self.period = (60 * 1)  # 1 minutes
        self.upload_timer = None
        try:
            self.averaging_period = config.log_file_averaging_period # TODO add these to config
        except AttributeError:
            self.averaging_period = config.averaging_period
        self.bridge_config = config

    def __str__(self):
        return self.str_name

    def start(self):
        max_bytes = self.bridge_config.log_file_max_bytes
        logFormatter = logging.Formatter("%(asctime)s %(message)s, ")
        #logger = logging.getLogger()
        self.log_pvdr.handlers = [] # this is necessary
        #self.log_pvdr.setLevel(logging.WARNING)
        self.log_pvdr.setLevel(logging.DEBUG)
        #print(self.colour_urls)
        for colour, f_path in self.colour_urls.items():
            #fileHandler = RotatingLogFileHandler(self.colour_urls[f_path], max_bytes, 10)
            logFileHandler = RotatingLogFileHandler(f_path, max_bytes, 3)
            logFileHandler.setFormatter(logFormatter)
            self.log_pvdr.addHandler(logFileHandler)
            logger.info(f"{colour}: {f_path} logger added")
            self.log_pvdr.info(f"{colour}: {f_path} logger added")
        
        #maxBytes = self.bridge_config.log_file_max_bytes # * 1024 * 1024
        #handler = logging.handlers.RotatingFileHandler(self.bridge_config.log_file_path, maxBytes=maxBytes)
        #self.log_pvdr.addHandler(fileHandler)

    #def update(self, tilt_status: TiltStatus):
    #    self.log_pvdr.warning(tilt_status.json())

    def enabled(self):
        return (self.colour_urls)
    
    def attach_archive(self, data_archive: TiltHistory):
        # keep a referene to the data queue, this is added after the object is created
        self.data_archive = data_archive

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
                    #print(tilt_status.toJson())
                    #status = await self.log_pvdr.info(json.dumps(tilt_status.__dict__, separators=(',', ':')))
                    #self.log_pvdr.info(tilt_status.toJson())
                    self.log_pvdr.info(self.prepare_payload(tilt_status))
                    #logger.debug(self.prepare_payload(tilt_status))
                    status = True
                    logger.debug(f"{self.str_name} updated for {colour} Tilt")
                else:
                    logger.info(f"{colour} has no data")
                return [status, wait_for] # either values or [None, None]
                
        #except requests.ConnectionError:
        #    logger.info('requests Connection error. todo: we need a task that periodically ensures WLAN connection is working')
        except Exception as e:
            logger.error(f"exception in provider.update: {e}")
        finally:
            return [False, False]
        
    def prepare_payload(self, tilt_status):
        # prepare the text to write to file
        #{"alcohol_by_volume": 3.38, "temp_celsius": 22.4, "original_gravity": 1.047, "degrees_plato": 5.6,
        #"gravity": 1.0219, "colour": "simulated", "name": "Festbier", "temp_fahrenheit": 72.4, "temp_valid": true,
        #"apparent_attenuation": 47.95, "hd": false, "gravity_valid": true}
        colour = tilt_status.colour + ", " if tilt_status.colour else ""
        name = tilt_status.name + ", " if tilt_status.name else ""
        temp = str(f"{tilt_status.temp_fahrenheit:.2f}") + "°F, " if self.temp_unit == "F" else str(f"{tilt_status.temp_celsius:.2f}") + "°C, "
        gravity = "SG " + str(f"{tilt_status.gravity:.4f}") + ", "
        abv = str(f"{tilt_status.alcohol_by_volume:.2f}") + "%ABV, " if tilt_status.original_gravity else ""
        attenuation = str(f"{tilt_status.apparent_attenuation:.2f}") + "%AA, " if tilt_status.original_gravity else ""
        
        out_str = f"{colour}{name}{abv}{attenuation}{temp}{gravity}"
        # trim any trailing ", "
        return (out_str[:-2] if out_str[-2:] == ", " else out_str)
        
        
    
    # takes dict of colours:filenames
    # returns list with all colours in lowercase letters for easier matching later
    @staticmethod
    def _normalise_colour_keys(colour_urls):
        normalised_colours = dict()
        try:
            for colour in colour_urls:
                normalised_colours[colour.lower()] = colour_urls[colour]
            return normalised_colours
        except:
            logger.error(f"config; log_file_tilt_colours must be dict: {colour_list}")
            raise Exception("Error in config for File provider, log_file_tilt_colours malformed")


    @staticmethod
    def _get_temp_unit(config: BridgeConfig):
        temp_unit = config.log_file_temp_unit.upper()
        if temp_unit == "C":
            return "C"
        elif temp_unit == "F":
            return "F"
        raise ValueError("temperature scale used by File provider must be F or C")
'''
class FileCloudProvider(implements(CloudProviderBase)):

    def __init__(self, config: PitchConfig):
        self.config = config
        self.str_name = "File ({})".format(config.log_file_path)
        self.logger = logging.getLogger(self.str_name)

    def __str__(self):
        return self.str_name

    def start(self):
        maxBytes = self.config.log_file_max_mb * 1024 * 1024
        handler = logging.handlers.RotatingFileHandler(self.config.log_file_path, maxBytes=maxBytes)
        self.logger.addHandler(handler)

    def update(self, tilt_status: TiltStatus):
        self.logger.warning(tilt_status.json())

    def enabled(self):
        return (self.config.log_file_path)
'''        