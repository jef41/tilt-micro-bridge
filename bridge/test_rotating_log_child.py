from rotating_file_handler import RotatingLogFileHandler
from logging import getLogger, DEBUG, Formatter

#handler = RotatingLogFileHandler(log_file_name, 200, 2)
#formatter = Formatter("%(message)s")
#handler.setFormatter(formatter)
logger = getLogger("test_main.child")
#logger.setLevel(DEBUG)

logger.info("child message")

def test():
    logger.info("child message from function")
