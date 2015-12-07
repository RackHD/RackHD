from config.settings import *
import logging
import pprint

LEVEL = [
    logging.CRITICAL, 
    logging.ERROR, 
    logging.WARNING, 
    logging.INFO, 
    logging.DEBUG
]

class Log(object):
    def __init__(self, *args, **kwargs):
        self._name = args[0] if args else __name__
        self._level = kwargs.get('level',LOGLEVEL)
        try:
            logging.basicConfig(level=LEVEL[self._level])
        except IndexError:
            logging.warning('Invalid log level %d, using default level', self._level)
        self.log = logging.getLogger(self._name)

    def critical(self,m,pprint=False):
        self.__log('critical',m,pprint)

    def info(self,m,pprint=False):
        self.__log('info',m,pprint)
    
    def debug(self,m,pprint=False):
        self.__log('debug',m,pprint)
    
    def error(self,m,pprint=False):
        self.__log('error',m,pprint)
    
    def warning(self,m,pprint=False):
        self.__log('warning',m,pprint)

    def __log(self,attr,m,pretty=False):
        if pretty: 
            m = pprint.pformat(m)
        return getattr(self.log,attr)(m)


