from rotating_file_handler import RotatingLogFileHandler
from logging import getLogger, DEBUG, Formatter

handler = RotatingLogFileHandler("rotating.log", 200, 2)
formatter = Formatter("%(message)s")
handler.setFormatter(formatter)
logger = getLogger("test_main")
logger.addHandler(handler)
logger.setLevel(DEBUG)


import test_rotating_log_child
#test_rotating_log_child.logger = getLogger("test_main.child")
test_rotating_log_child.logger.addHandler(handler)
test_rotating_log_child.logger.setLevel(DEBUG)

test_rotating_log_child.test()


logger.info("message")