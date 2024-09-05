''' create a root logger
    duplicate console output to a file
    keep at most 10 log files - new file on each restart
'''

import logging, sys, os, io


def get_log_file():
    for i in range(10):
        fn = "debug_" + str(i) + ".log"
        try:
            f = open(fn, "r")
            # continue with the file.
        except OSError:  # open failed
           fn = "debug_0.log" if i == 6 else fn
           break
    return fn

log_file = get_log_file()

class logToFile(io.IOBase):
    def __init__(self):
        pass
 
    def write(self, data):
        with open(log_file, mode="a+") as f:
            f.write(data)
        return len(data)


logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s]:%(name)s:\t(message)s")

my_logger = logging.getLogger('my_app')  # Parent logger
 
# now your console text output is saved into file
os.dupterm(logToFile())

import test_module1_logger
import test_module2_logger



# test message
my_logger.info("test1")
#module1_logger = logging.getLogger('main.module1')
test_module1_logger.hello()

# disable logging to file
os.dupterm(None)


