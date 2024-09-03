import logging, sys#, os
#logging.basicConfig(level=logging.DEBUG)
'''logging.basicConfig(filename="/debug.log",
                    filemode="a",
                    level=logging.DEBUG,
                    stream=sys.stdout,
                    force=False)'''
#logging.basicConfig(filename="/debug.log",
#                    filemode="a",
#                    level=logging.DEBUG)
logging.basicConfig(stream=sys.stdout,
                    level=logging.DEBUG)
for handler in logging.getLogger().handlers:
    handler.setFormatter(logging.Formatter("%(asctime)s: [%(levelname)s]:%(name)s:%(message)s"))
# Create a logger specifically for the main module
my_logger = logging.getLogger('my_app')  # Parent logger
'''
# Configure the logger
my_logger.setLevel(logging.DEBUG)  # Set the logging level for other modules

# Create a console handler and set the format
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s: %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Create a file handler and set the format
file_handler = logging.FileHandler('app.log', mode='a+')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s: file%(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
# Add handlers to the my logger
#logging.getLogger().addHandler(console_handler)
#logging.getLogger().addHandler(file_handler)

# set my logger
#logging.basicConfig(level=logging.DEBUG)
#for handler in my_logger.handlers: # logging.getLogger('main').handlers:
#    handler.setFormatter(logging.Formatter("%(asctime)s: %(name)s - %(levelname)s - %(message)s"))
 
#logger = logging.getLogger('main')
#logger.setLevel(logging.DEBUG) # level for this module
# Add handlers to the logger
#logger.addHandler(console_handler)
#logger.addHandler(file_handler)
my_logger.addHandler(console_handler)
my_logger.addHandler(file_handler)
#logging.basicConfig.addHandler(console_handler)
#logging.basicConfig.addHandler(file_handler)
'''
# test message
my_logger.info("test1")
#module1_logger = logging.getLogger('main.module1')

import test_module1_logger
import test_module2_logger

test_module1_logger.hello()

'''
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
for handler in logging.getLogger("test").handlers:
    handler.setFormatter(logging.Formatter("[%(levelname)s]:%(name)s:%(message)s"))
logging.info("hello upy")
logging.getLogger("child").info("hello 2")
logging.getLogger("child2").debug("hello 2")
'''