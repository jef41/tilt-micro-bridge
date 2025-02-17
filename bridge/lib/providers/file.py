'''
    save data to local csv files
'''
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
    document size & number of log files - xx free space 
    os.statvfs("/") - first is block size, 3rd is free blocks (4096 * 121 ) /1024 = 484kb
    set debug and file_log sizes in bridge_config.py - as a list
    keep file sizes to within multiples of 44096bytes to use full blocks only
'''
logger = logging.getLogger('File_pvdr')
logger.info("Startup")

#class CSVFileProvider(CloudProviderBase):
class CSVFileProvider():
    # expect a single instance of this class
    def __init__(self, config: BridgeConfig):
        self.bridge_config = config
        #self.temp_unit = CSVFileProvider._get_temp_unit(config)
        self.temp_unit = self._get_temp_unit(self.bridge_config)
        self.colour_urls = self._get_colour_dict()
        self.colours_enabled = self.colour_urls # TODO: improve on this, colour_urls as an object?
        self.str_name = f"CSV Logger"
        self.log_pvdr = logging.getLogger(self.str_name)
        self.csv_loggers = dict() # collection of loggers
        self.rate = 1
        self.period = (60 * 1)  # 1 minute TODO: read from config
        self.upload_timer = None
        try:
            self.averaging_period = self.bridge_config.csv_log_averaging_period
        except AttributeError:
            self.averaging_period = self.bridge_config.averaging_period

    def __str__(self):
        return self.str_name

    def start(self):
        max_bytes = (self.bridge_config.csv_log_max_kb * 1024) - 800 # -800 should keep log files within 4096 block boundry
        # TODO: max bytes should be calculated from free disk space - log file size from config
        # ((( disk space - (debug log size * number) ) / number of log files ) % 4096 ) -800
        '''
        logFormatter = logging.Formatter("%(asctime)s, %(message)s")
        #logger = logging.getLogger()
        self.log_pvdr.handlers = [] # this is necessary
        #self.log_pvdr.setLevel(logging.WARNING)
        self.log_pvdr.setLevel(logging.DEBUG)
        #print(self.colours_enabled)
        #print(f"***   dict:{self.colour_urls}   ***")
        '''
        for colour, f_path in self.colours_enabled.items():
            '''
            #fileHandler = RotatingLogFileHandler(self.colours_enabled[f_path], max_bytes, 10)
            # use brew name, or colour for filename
            fname = f_path if f_path else colour
            logFileHandler = RotatingLogFileHandler(fname + ".log", max_bytes, 5)
            logFileHandler.setFormatter(logFormatter)
            self.log_pvdr.addHandler(logFileHandler)
            logger.info(f"{colour} Tilt: {fname  + ".log"} logger added")
            namestr = ": " + f_path  if f_path else ""
            self.log_pvdr.info(f"{colour} Tilt{namestr} logger added")
            # TODO: add a log line about OG & columns below
            '''
            if colour not in self.csv_loggers:
                self.csv_loggers[colour] = self._get_new_logger(colour, max_bytes, f_path)

    def enabled(self):
        #print(f"***   enabled?{self.colours_enabled}   ***")
        #return (self.colours_enabled)
        return True if self.colours_enabled else False
    
    def attach_archive(self, data_archive: TiltHistory):
        # keep a reference to the data queue, this is added to the class after the object is initially created
        self.data_archive = data_archive

    async def update(self):
        # 
        log_period = self.period//self.rate # older than this = stale data, ensure this is an integer of seconds
        if self.averaging_period > log_period:
            raise Exception(f"Error in config for {self.str_name} provider: Invalid combination of log ({log_period}) & averaging ({self.averaging_period}) periods")
        try:
            for colour in self.colours_enabled:
                status, wait_for = [None, None] 
                tempF, SG = self.data_archive.get_data(colour, av_period=self.averaging_period, log_period=log_period)
                if tempF and SG:
                    tilt_status = TiltStatus(colour, tempF, SG, self.bridge_config)
                    #print(tilt_status.toJson())
                    #status = await self.log_pvdr.info(json.dumps(tilt_status.__dict__, separators=(',', ':')))
                    #self.log_pvdr.info(tilt_status.toJson())
                    
                    #self.log_pvdr.info(self.prepare_payload(tilt_status))
                    
                    status, wait_for = self.csv_loggers[colour].log_data(tilt_status)
                    
                    #logger.debug(self.prepare_payload(tilt_status))
                    status = True
                    logger.debug(f"{self.str_name} updated for {colour} Tilt")
                else:
                    logger.info(f"{colour} has no data")
                #return [status, wait_for] # either values or [None, None]
        except Exception as e:
            logger.error(f"exception in provider.update: {e}")
            status, wait_for = [False, None] 
        finally:
            return [status, wait_for]
        
    '''
    def prepare_payload(self, tilt_status):
        # prepare the text to write to file
        # TODO if it is the first log then add a header line
        colour = tilt_status.colour + ", " if tilt_status.colour else ""
        name = tilt_status.name + ", " if tilt_status.name else ""
        temp = str(f"{tilt_status.temp_fahrenheit:.2f}") + "°F, " if self.temp_unit == "F" else str(f"{tilt_status.temp_celsius:.2f}") + "°C, "
        gravity = "SG " + str(f"{tilt_status.gravity:.4f}") + ", "
        abv = str(f"{tilt_status.alcohol_by_volume:.2f}") + "%ABV, " if tilt_status.original_gravity else ""
        attenuation = str(f"{tilt_status.apparent_attenuation:.2f}") + "%AA, " if tilt_status.original_gravity else ""
        
        out_str = f"{colour}{name}{abv}{attenuation}{temp}{gravity}"
        # trim any trailing ", "
        return (out_str[:-2] if out_str[-2:] == ", " else out_str)
    '''
    
    def _get_new_logger(self, colour, max_bytes, f_name):
        return CSVLogger(colour, max_bytes, self.temp_unit, f_name) 
    
    
    # takes list of colours
    # returns dict with all colours in lowercase letters for easier matching later
    # if set, key is set to brew name
    def _get_colour_dict(self):
        #normalised_colours = list()
        normalised_colours = dict()
        #try:
        colours_config = self.bridge_config.csv_log_tilt_colours
        if colours_config:
            for colour in colours_config:
                #print(f"\ngetting colours {colour}")
                lower_colour = colour.lower()
                #print(lower_colour)
                brew_name = self.bridge_config.get_brew_name(lower_colour)
                # if we have a beer name then add to the dict
                if brew_name.lower() == lower_colour:
                    normalised_colours[lower_colour] = ""
                else:
                    normalised_colours[lower_colour] = brew_name
        #print(normalised_colours)
        return normalised_colours
        #except:
        #    logger.error(f"config; csv_log_tilt_colours must be formatted as a JSON list")
        #    raise Exception("Error in config for File provider, csv_log_tilt_colours malformed")
        #finally:
        #    return normalised_colours


    @staticmethod
    def _get_temp_unit(config: BridgeConfig):
        temp_unit = config.csv_log_temp_unit.upper()
        if temp_unit == "C":
            return "C"
        elif temp_unit == "F":
            return "F"
        raise ValueError("temperature scale used by File provider must be F or C")


class CSVLogger():
    '''
        collection of loggers - one for each Tilt
        if we have > 1 Tilt storage space will be an issue - manual or auto handling
        of max file size?
    '''
    def __init__(self, colour, size_b, temp_unit, brew_name=None):
        #super().__init__(temp_unit) # get parent methods
        #print(f"***  temp_unit{self.temp_unit}")
        self.temp_unit = temp_unit
        self.tilt_log = logging.getLogger(colour)
        # use brew name, or colour for filename
        fname = brew_name if brew_name else colour
        #max_bytes = (self.bridge_config.csv_log_max_kb * 1024) - 800 # -800 should keep log files within 4096 block boundry
        logFormatter = logging.Formatter("%(asctime)s, %(message)s")
        logFileHandler = RotatingLogFileHandler(fname + ".log", size_b, 5)
        logFileHandler.setFormatter(logFormatter)
        self.tilt_log.addHandler(logFileHandler)
        logger.info(f"{colour} Tilt: {fname  + ".log"} logger added")
        namestr = ": " + brew_name if brew_name else ""
        self.tilt_log.info(f"{colour} Tilt{namestr} logger added")
        self.initial = True
    
    def log_data(self, tilt_status):
        
        result = self.tilt_log.info(self._prepare_payload(tilt_status))
        #return [status, wait_for]
        # TODO improve/add test
        return [True, None]
    
    def _prepare_payload(self, tilt_status):
        # TODO needs a tidy up after testing correct data is logged to correct file(s)
        #self.tilt_status = tilt_status
        colour = tilt_status.colour + ", " if tilt_status.colour else ""
        #namestr = " for " + tilt_status.name if tilt_status.name else ""
        if tilt_status.name == tilt_status.colour:
            namestr = ""
        else:
            namestr = " for " + tilt_status.name
        if self.initial:
            # log header line(s)
            units = self._get_parameters(tilt_status, self.temp_unit)
            #Title case the Tilt Colour
            self.tilt_log.info(f"\nHeader: {tilt_status.colour[0].upper() + tilt_status.colour[1:].lower()} Tilt{namestr}\n{units}")
            # log field names/units
            self.initial = False
        
        # TODO: sort out temp unit
        if self.temp_unit == "C":
            temp = str(f"{tilt_status.temp_celsius:.2f}") + "°C, "
        else:
            temp = str(f"{tilt_status.temp_fahrenheit:.2f}") + "°F, " #  if self.temp_unit == "F" else str(f"{tilt_status.temp_celsius:.2f}") + "°C, "
        gravity = (f"{tilt_status.gravity:.4f}") + ", "
        abv = str(f"{tilt_status.alcohol_by_volume:.2f}") + ", " if tilt_status.original_gravity else ""
        attenuation = str(f"{tilt_status.apparent_attenuation:.2f}") + ", " if tilt_status.original_gravity else ""
        if namestr:
            namestr = namestr[5:] + ", "
        out_str = f"{colour}{namestr}{abv}{attenuation}{temp}{gravity}"
        # trim any trailing ", "
        return (out_str[:-2] if out_str[-2:] == ", " else out_str)
    
    @staticmethod
    def _get_parameters(tilt_status, temp_unit):
        params = "timestamp, Tilt colour"
        #if tilt_status.name:
        if tilt_status.name == tilt_status.colour:
            pass
        else:
            params += ", Name"
        if tilt_status.original_gravity:
            params += ", %ABV, %Apparent Attenuation"
        #params += f", Temperature ({CSVFileProvider.temp_unit}), Specific Gravity"
        params += f", Temperature ({temp_unit}), Specific Gravity"
        return params
        
       