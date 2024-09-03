#import logging
#my_logger_test = logging.getLogger('main.module2') 
#my_logger_test.info("module2_test")
import logging
# https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library
#logging.getLogger('foo').addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)
logger.debug('This is a test log message.')