'''
    save data to local csv files
'''
import time
import logging
from logging import RotatingLogFileHandler, TimedRotatingLogFileHandler
#from logging import RotatingLogFileHandler
#from rotating_file_handler import RotatingLogFileHandler
from models import TiltStatus
from models import TiltHistory
from abstractions import BridgeProviderBase
from configuration import BridgeConfig
import asyncio
#import async_urequests as requests
import json
from os import statvfs, stat
from math import ceil
#import gc # for development only
#from machine import Timer
''' TODO
    if max_bytes initially returns a v small value then we immeidately get 5 log files
    maybe initial max_bytes should just check if 4kb x no log files available? if not return stop with error indicator
    done around 97 re-assign rotatinglog file size if necessary
    done change to CSV
    log file names to dict colours enabled
'''
logger = logging.getLogger('File_csv_pvdr')
logger.info("Startup")

'''
class TimedRotatingLogFileHandler(RotatingLogFileHandler):
    # add a timer based flush, triggered from emit
    # async routine to set flush_flag
    # override FileHandler
    def __init__(self,
                 file_full_name: str,
                 max_file_size_in_bytes: int,
                 number_of_backup_files: int,
                 write_secs : int):
        #RotatingLogFileHandler.__init__(self)
        super(TimedRotatingLogFileHandler, self).__init__(file_full_name,
                                                          max_file_size_in_bytes,
                                                          number_of_backup_files
                                                          ) # track down my subclasses please
        # add a log flush timer
        self.force_flg = False
        asyncio.create_task(self.force_write_tmr(write_secs)) # flush the log to file (secs)
    
    async def force_write_tmr(self, tmout):
        # stop printing data: statements to serial
        # self.flush_tmr = False
        #print("***  self print raw started")
        while True:
            await asyncio.sleep(tmout) 
            #print("***  log flush timer set")
            self.force_flg = True
            #if hasattr(self.stream, "flush"):
            # hacky TDO
            #self.handlers[0].flush()
    
    def force_write(self):
        # internmittenlty called to force a file write - in case of power fail
        #if self.stream and hasattr(self.stream, "flush"):
        #print(f"flush {self.file_full_name}")
        #self.stream.flush()
        self.force_flg = False
        with self.rotating_log_file_handler_lock:
            self.current_log_file.close()
            self.current_log_file = open(self.file_full_name, "a")
    
    def emit(self, record):
        super().emit(record)
        if self.force_flg:
            self.force_write()
'''

class CSVFileProvider(BridgeProviderBase):
    #class CSVFileProvider():
    # expect a single instance of this class
    def __init__(self, config: BridgeConfig):
        self.bridge_config = config
        #self.temp_unit = CSVFileProvider._get_temp_unit(config)
        self.temp_unit = self._get_temp_unit(self.bridge_config)
        self.col_dest = self._get_colour_dict() # colour:filename.csv
        #self.colour_urls = self.col_dest # TODO: improve on this, col_dest as an object?
        self.str_name = f"CSV Logger"
        self.log_pvdr = logging.getLogger(self.str_name)
        self.csv_loggers = dict() # collection of loggers
        self.rate = 1 # self.bridge_config.csv_log_rate
        self.csv_bkp_count = config.csv_bkp_count
        self.period = self.bridge_config.csv_log_period  # seconds
        self.upload_timer = None
        try:
            self.averaging_period = self.bridge_config.csv_log_averaging_period
        except AttributeError:
            self.averaging_period = self.bridge_config.averaging_period
        #self.log_pvdr.csv_timer = Timer(
        #    mode=Timer.ONE_SHOT, period=30_000, callback=self._timeout_callback
        #)
        self.csv_flush = False

    #def _timeout_callback(self, timer):
    #    self.csv_flush = True
    #    logger.debug(f"csv flsuh flag reset")
    
    def __str__(self):
        return self.str_name

    def start(self):
        # initialise relevant loggers
        max_bytes = self._calc_log_size(len(self.col_dest), self.csv_bkp_count)
        logger.debug(f"initial  max_bytes {max_bytes}")
        #max_bytes = (self.bridge_config.csv_log_max_kb * 1024) - 800 # -800 should keep log files within 4096 block boundry
        # TODO: max bytes should be calculated from free disk space - log file size from config
        # ((( disk space - (debug log size * number) ) / number of log files ) % 4096 ) -800
        '''
        logFormatter = logging.Formatter("%(asctime)s, %(message)s")
        #logger = logging.getLogger()
        self.log_pvdr.handlers = [] # this is necessary
        #self.log_pvdr.setLevel(logging.WARNING)
        self.log_pvdr.setLevel(logging.DEBUG)
        #print(self.col_dest)
        #print(f"***   dict:{self.col_dest}   ***")
        '''
        for colour, f_path in self.col_dest.items():
            '''
            #fileHandler = RotatingLogFileHandler(self.col_dest[f_path], max_bytes, 10)
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
                self.csv_loggers[colour] = self._get_new_logger(colour, f_path, max_bytes)
        # TODO now need to iterate through all the loggers, check how many of those log files already exist
        # then reallocate size accordingly
        # TODO read debug log files names rather than hardcode
        file_check_list = self._get_filenames() #["debug.log", "debug.log.1"]
        for logger_col in self.csv_loggers:
            file_check_list += self._get_filenames(logging.getLogger(logger_col))
            '''
            #logging.getLogger().handlers[0].max_file_size_in_bytes
            test = logging.getLogger(name).handlers[0].file_full_name
            file_check_list += [test]
            #number of backup files
            count = logging.getLogger(name).handlers[0].number_of_backup_files
            #print(f"{test} {count}")
            for c in range(count):
                file_check_list += [f"{test}.{c+1}"]
            #if isinstance(CSVFileProvider)
            '''
        #print(*file_check_list, ', ')
        max_bytes = self._calc_log_size(len(self.col_dest), self.csv_bkp_count, file_check_list)
        #colln = ', '.join(*self.csv_loggers)
        # print(*self.csv_loggers)
        #TODO reiterate & reassign each logfile handler size
        for name in self.csv_loggers:
            logging.getLogger(name).handlers[0].max_file_size_in_bytes = max_bytes
        logger.info(f"CSV max_bytes reassigned to:{max_bytes}")

    def enabled(self):
        #print(f"***   enabled?{self.col_dest}   ***")
        #return (self.col_dest)
        return True if self.col_dest else False
    
    def attach_archive(self, data_archive: TiltHistory):
        # keep a reference to the data queue, this is added to the class after the object is initially created
        self.data_archive = data_archive

    async def update(self):
        # 
        log_period = self.period//self.rate # older than this = stale data, ensure this is an integer of seconds
        if self.averaging_period > log_period:
            raise Exception(f"Error in config for {self.str_name} provider: Invalid combination of log ({log_period}) & averaging ({self.averaging_period}) periods")
        try:
            for colour in self.col_dest:
                status, wait_for = [None, None] 
                tempF, SG = self.data_archive.get_data(colour, av_period=self.averaging_period, log_period=log_period)
                if tempF and SG:
                    tilt_status = TiltStatus(colour, tempF, SG, self.bridge_config)
                    # data offsets/calibration is applied here in TiltStatus
                    #print(tilt_status.toJson())
                    #status = await self.log_pvdr.info(json.dumps(tilt_status.__dict__, separators=(',', ':')))
                    #self.log_pvdr.info(tilt_status.toJson())
                    
                    #self.log_pvdr.info(self.prepare_payload(tilt_status))
                    
                    status, wait_for = self.csv_loggers[colour].log_data(tilt_status)
                    
                    #logger.debug(self.prepare_payload(tilt_status))
                    #status = True
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
    
    def _get_new_logger(self, colour, f_name, max_bytes):
        return CSVLogger(colour, f_name, max_bytes, self.temp_unit, self.csv_bkp_count) 
        
    def _get_colour_dict(self):
        # takes list of colours
        # returns dict with all colours in lowercase & filename
        # if set, key is set to brew name
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
                    normalised_colours[lower_colour] = lower_colour + ".csv"
                else:
                    normalised_colours[lower_colour] = brew_name + ".csv"
        #print(normalised_colours)
        return normalised_colours
        #except:
        #    logger.error(f"config; csv_log_tilt_colours must be formatted as a JSON list")
        #    raise Exception("Error in config for File provider, csv_log_tilt_colours malformed")
        #finally:
        #    return normalised_colours

    @staticmethod
    def _calc_log_size(tilt_count, csv_bkp_count, check_for=('debug.log','debug.log.1')):
        ''' from free disk space calculate log file sizes
            the debug.log size is also declared in config, so could be passed in
            tries to allocate whole blocks 
        '''
        #logging.getLogger().handlers[0].max_file_size_in_bytes - root logger
        #((( disk space - (debug log size * number) ) / number of log files ) % 4096 ) -800
        f_info = statvfs('/')
        # Check handlers in the parent (root) logger
        ''' returns "Logger object has no attribute parent"
        parent_logger = logger
        while parent_logger:
            for handler in parent_logger.handlers:
                if isinstance(handler, RotatingLogFileHandler):
                    print("Log file max size:", handler.max_file_size_in_bytes)
            parent_logger = parent_logger.parent if parent_logger.parent else None
        '''
        # TODO read filenames rather than hardcode them
        already_allocated_dbg_blocks = check_for_existing_files(check_for)
        # TODO below is hacky - assumes we have a root logger
        debug_max_bytes = logging.getLogger().handlers[0].max_file_size_in_bytes
        debug_count = 1 + logging.getLogger().handlers[0].number_of_backup_files
        debug_blocks = ceil((debug_max_bytes * debug_count / f_info[0]))
        
        nbr_files = tilt_count * (csv_bkp_count + 1) # TODO retrieve count of colours * number to keep+1
        spare_blocks = 1
        #csv_bkp_count = 4 # TODO read from config?
        
        free_blocks = f_info[3] - debug_blocks - spare_blocks + already_allocated_dbg_blocks
        blocks_per_csv = free_blocks // nbr_files
        max_size_bytes = blocks_per_csv * f_info[0]
        allocated_blocks = (blocks_per_csv * nbr_files) + debug_blocks + spare_blocks
        unallocated_blocks = f_info[3] - allocated_blocks
        
        # TODO test if log size is unfeasibly small & alert/error fail
        '''
        print(f'debug.log is {debug_blocks} blocks {(debug_max_bytes * debug_count)/1024}kb')
        print(f"recording for {tilt_count} Tilts, {nbr_files} files total")
        print(f"free blocks are {free_blocks} = {f_info[3]} - {debug_blocks} - {spare_blocks}")
        print(f"blocks_per_csv = {free_blocks} // {nbr_files} = {free_blocks // nbr_files}")
        print(f"max_bytes {max_size_bytes}")
        print(f"unallocated space will be {f_info[3]} - {allocated_blocks} = {unallocated_blocks} blocks")
        '''
        return max_size_bytes

    @staticmethod
    def _get_temp_unit(config: BridgeConfig):
        temp_unit = config.csv_log_temp_unit.upper()
        if temp_unit == "C":
            return "C"
        elif temp_unit == "F":
            return "F"
        raise ValueError("temperature scale used by File provider must be F or C")
    
    @staticmethod
    def _get_filenames(logger_name=logging.getLogger()):
        # return a list of filenames, by default looks at root logger
        # TODO should have try catch in case handler[0] is not RotatingLogFIleHandler, or loop until we get that handler
        file_check_list = []
        test = logger_name.handlers[0].file_full_name
        file_check_list += [test]
        #number of backup files
        count = logger_name.handlers[0].number_of_backup_files
        #print(f"***  {test} {count}")
        for c in range(count):
            file_check_list += [f"{test}.{c+1}"]
        #print(*file_check_list, ', ')
        return file_check_list


class CSVLogger():
    '''
        collection of loggers - one for each Tilt
        if we have > 1 Tilt storage space will be an issue - manual or auto handling
        of max file size?
    '''
    #def __init__(self, colour, size_b, temp_unit, csv_bkp_count, brew_name=None):
    def __init__(self, colour, fname, size_b, temp_unit, csv_bkp_count):
        #super().__init__(temp_unit) # get parent methods
        #print(f"***  temp_unit{self.temp_unit}")
        self.temp_unit = temp_unit
        self.tilt_log = logging.getLogger(colour)
        # use brew name, or colour for filename
        #fname = brew_name if brew_name else colour
        #max_bytes = (self.bridge_config.csv_log_max_kb * 1024) - 800 # -800 should keep log files within 4096 block boundry
        logFormatter = logging.Formatter("%(asctime)s, %(message)s")
        #logFileHandler = RotatingLogFileHandler(fname + ".log", size_b, csv_bkp_count)
        #print("about to raise an error?")
        logFileHandler = TimedRotatingLogFileHandler(fname, size_b, csv_bkp_count, 900)
        logFileHandler.setFormatter(logFormatter)
        self.tilt_log.addHandler(logFileHandler)
        logger.info(f"{colour} Tilt: {fname} logger added")# {size_b/1024}kb per file")
        #namestr = ": " + brew_name if brew_name else ""
        namestr = ": " if fname[:-4] == colour else ": " + fname[:-4] # if present add beer name
        self.tilt_log.info(f"{colour[0].upper() + colour[1:].lower()} Tilt{namestr} logger added")
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
            self.tilt_log.info(f"Header: {tilt_status.colour[0].upper() + tilt_status.colour[1:].lower()} Tilt{namestr}\n{units}")
            # log field names/units
            self.initial = False
        
        if self.temp_unit == "C":
            #temp = str(f"{tilt_status.temp_celsius:.2f}") + "°C, "
            temp = str(f"{tilt_status.temp_celsius:.1f}") + ", "
        else:
            #temp = str(f"{tilt_status.temp_fahrenheit:.2f}") + "°F, " #  if self.temp_unit == "F" else str(f"{tilt_status.temp_celsius:.2f}") + "°C, "
            temp = str(f"{tilt_status.temp_fahrenheit:.1f}") + ", "
        gravity = (f"{tilt_status.gravity:.4f}") + ", "
        abv = str(f"{tilt_status.alcohol_by_volume:.2f}") + ", " if tilt_status.original_gravity else ""
        attenuation = str(f"{tilt_status.apparent_attenuation:.2f}") + ", " if tilt_status.original_gravity else ""
        #if namestr:
        #    namestr = namestr[5:] + ", "
        #out_str = f"{colour}{namestr}{abv}{attenuation}{temp}{gravity}"
        out_str = f"{abv}{attenuation}{temp}{gravity}"
        # trim any trailing ", "
        return (out_str[:-2] if out_str[-2:] == ", " else out_str)
    
    @staticmethod
    def _get_parameters(tilt_status, temp_unit):
        params = "timestamp"
        #params = "timestamp, Tilt colour"
        #if tilt_status.name == tilt_status.colour:
        #    pass
        #else:
        #    params += ", Name"
        if tilt_status.original_gravity:
            params += ", ABV (%), Apparent Attenuation (%)"
        #params += f", Temperature ({CSVFileProvider.temp_unit}), Specific Gravity"
        params += f", Temperature (°{temp_unit}), Specific Gravity"
        return params


def check_for_existing_files(file_names: list):
    # check for exisiting debug logs and return the number of blocks used by them
    used_blocks = 0
    for dbg_file in file_names:
        try:
            used_bytes = stat(dbg_file)[6] if stat(dbg_file) else 0
            if used_bytes:
                used_blocks += ceil(used_bytes / statvfs('/')[0])
        except OSError as e:
            # print(f"caught {e} {dbg_file} {used_blocks}")
            # file not found
            pass
        except Exception as e:
            print(e)
    return used_blocks
