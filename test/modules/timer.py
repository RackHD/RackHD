from logger import Log
from threading import Timer

LOG = Log(__name__)

class TimerTask(object):
    def __init__(self, 
                 interval=5, 
                 daemon=True, 
                 function=None, 
                 *args, 
                 **kwargs):
        self.args       = args
        self.kwargs     = kwargs
        self._timer     = None
        self._interval   = interval
        self._function   = function
        self._is_running = False
        self._daemon     = daemon
        self.start()

    def _run(self):
        self._is_running = False
        self.start()
        self._function(*self.args, **self.kwargs)

    def start(self):
        if not self._is_running:
            LOG.debug('start: {0}'.format(self))
            self._timer = Timer(self._interval, self._run)
            self._timer.daemon = self._daemon
            self._timer.start()
            self._is_running = True

    def stop(self):
        self._timer.cancel()
        self._is_running = False
