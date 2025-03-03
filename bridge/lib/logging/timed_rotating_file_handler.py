import asyncio
import logging
from logging.rotating_file_handler import RotatingLogFileHandler

class TimedRotatingLogFileHandler(RotatingLogFileHandler):
    # add a timer based flush, triggered from emit
    # async routine to set flush_flag
    # override FileHandler
    def __init__(self,
                 file_full_name: str,
                 max_file_size_in_bytes: int,
                 number_of_backup_files: int,
                 write_secs : int):
        super(TimedRotatingLogFileHandler, self).__init__(file_full_name,
                                                          max_file_size_in_bytes,
                                                          number_of_backup_files
                                                          ) # track down my subclasses please
        # add a log flush timer
        self.force_flg = False
        asyncio.create_task(self.force_write_tmr(write_secs)) # flush the log to file (secs)
    
    async def force_write_tmr(self, tmout):
        # set flag to flush after next write
        while True:
            await asyncio.sleep(tmout) 
            #print("***  log flush timer set")
            self.force_flg = True
    
    def force_write(self):
        # if flag is set flush file to disk, in case of power fail
        self.force_flg = False
        with self.rotating_log_file_handler_lock:
            #self.current_log_file.close()
            #self.current_log_file = open(self.file_full_name, "a")
            #print('#   about to flush TRLF handler')
            self.current_log_file.flush()
    
    def emit(self, record):
        super().emit(record)
        if self.force_flg:
            self.force_write()
