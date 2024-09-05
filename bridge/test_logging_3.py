import logging, sys
logFormatter = logging.Formatter("%(asctime)s [%(name)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()
rootLogger.handlers = []
rootLogger.setLevel(logging.DEBUG)

fileHandler = logging.FileHandler("duallog.txt")
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler() #logging.StreamHandler(logging.StreamHandler(sys.stdout))
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

import test_logging_3_moduleA

print("run")
rootLogger.info("test")