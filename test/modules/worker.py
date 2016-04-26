from logger import Log
from threading import Thread
from datetime import datetime, timedelta
import time

LOG = Log(__name__)

"""
Class to abstract threaded worker subtasks
:param id: node identifier 
:param worker: the subtask worker object
"""
class WorkerThread(object):
    def __init__(self,worker,id):
        self.id = id
        self.worker = worker
        self.thread = None
        self.running = False
        self.start_time = 0
        self.timeout = False

"""
Class to construct a threaded worker
:param func: thread target function
:param tasks: list of subtasks (WorkerThread)
:param daemon: option to run task thread daemonized
"""
class WorkerTasks(object):
    def __init__(self,**kwargs):
        self.__func = kwargs.get('func')
        self.__tasks = kwargs.get('tasks')
        self.__daemon = kwargs.get('daemon',True)
        if not isinstance(self.__tasks, list):
            raise TypeError('expected thread task list')
        if not hasattr(self.__func, '__call__'):
            raise TypeError('expected callable function')
    
    def __wait(self, timeout_sec):
        while len(self.__tasks):
            for task in self.__tasks:
                elapsed_time = int(time.mktime(datetime.now().timetuple()) - task.start_time)
                if timeout_sec != -1 and elapsed_time >= timeout_sec:
                    LOG.error('subtask timeout after {0} seconds, (id={1}), stopping..' \
                        .format(elapsed_time,task.id))
                    task.worker.stop()
                    task.running = False
                    task.timeout = True
                if not task.running:
                    self.__stop(task)
            time.sleep(1)

    def __stop(self, task):
        LOG.info('stopping subtask for {0}'.format(task.id))
        task.thread.join()
        try:
            self.__tasks.remove(task)
        except IndexError:
            LOG.error('index error while removing subtask from list!')
				
    def __run(self):
        for task in self.__tasks:
	        task.thread = Thread(target=self.__func, \
                                     args=(task.worker,task.id,))
	        task.thread.daemon = self.__daemon
	        task.start_time = time.mktime(datetime.now().timetuple())
	        task.running = True
	        task.thread.start()
    
    def run(self):
        self.__run()
	
    def wait_for_completion(self, timeout_sec=300):
        self.__wait(timeout_sec)
	
