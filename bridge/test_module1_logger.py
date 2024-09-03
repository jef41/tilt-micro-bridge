import logging
#module_logger = logging.getLogger('main.module1')
#module_logger = logging.getLogger('main')
#module_logger.info(__name__ + ' imported')
my_logger = logging.getLogger('my_app.module1')
my_logger.info(__name__ + ' imported')

def hello():
    my_logger.info('hello')