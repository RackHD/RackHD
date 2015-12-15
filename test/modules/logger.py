from config.settings import *
import logging
from json import dumps,loads

LEVEL = [
    logging.CRITICAL, 
    logging.ERROR, 
    logging.WARNING, 
    logging.INFO, 
    logging.DEBUG
]

"""
Class to abstract python logging functionality
:param name: optional logging name
:param level: optional logging level, default defined in config/settings.py
"""
class Log(object):
    def __init__(self, *args, **kwargs):
        self._name = args[0] if args else __name__
        self._level = kwargs.get('level',LOGLEVEL)
        try:
            logging.basicConfig(level=LEVEL[self._level], format=LOGFMT)
        except IndexError:
            logging.warning('Invalid log level %d, using default level', self._level)
        self.log = logging.getLogger(self._name)

    def critical(self,m,json=False):
        self.__log('critical',m,json)

    def info(self,m,json=False):
        self.__log('info',m,json)
    
    def debug(self,m,json=False):
        self.__log('debug',m,json)
    
    def error(self,m,json=False):
        self.__log('error',m,json)
    
    def warning(self,m,json=False):
        self.__log('warning',m,json)

    def __log(self,attr,m,json=False):
        if json:
            m = dumps(m,sort_keys=True,indent=4,separators=(',', ': ')) \
                    .decode('string-escape')
        return getattr(self.log,attr)(m)


