from config.auth import *
from config.settings import *
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from logger import Log
from worker import WorkerThread, WorkerTasks
import SocketServer
import signal
import thread
import pxssh
from json import loads

LOG = Log(__name__)

class BaseHandler(BaseHTTPRequestHandler): 
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
    
    def do_HEAD(self):
        self._set_headers()
   
class DefaultRequestHandler(BaseHandler):
    def do_GET(self):
        self._set_headers()
            
    def do_PUT(self):
        self._set_headers()
        
    def do_PATCH(self):
        self._set_headers()
        
    def do_POST(self):
        self._set_headers()
        content_length = int(self.headers.getheader('content-length'),0)
        body = loads(self.rfile.read(content_length))
        LOG.info(body,json=True)
        
class Httpd(object):
    def __init__(self, *args, **kwargs):
        self.__address = kwargs.get('address','0.0.0.0')
        self.__port = kwargs.get('port', 80);
        self.__handler_class = kwargs.get('handler_class', DefaultRequestHandler)
        self.httpd = HTTPServer((self.__address, self.__port), self.__handler_class)
    
    def start(self):
        LOG.info('Starting httpd server on {0} port {1}'.format(self.__address, self.__port))
        self.httpd.serve_forever()
        
    def stop(self):
        LOG.info('Stopping httpd server')
        self.httpd.shutdown()

def open_ssh_forward(local_port):
    session = pxssh.pxssh()
    session.SSH_OPTS = (session.SSH_OPTS
                     + " -o 'StrictHostKeyChecking=no'"
                     + " -o 'UserKnownHostsFile=/dev/null' "
                     + " -o 'IdentitiesOnly=yes' "
                     + " -p " + str(SSH_PORT)
                     + " -R " + str(local_port) + ':localhost:' + str(HTTPD_PORT))

    session.force_password = True
    session.login(HOST_IP, SSH_USER, SSH_PASSWORD, port=SSH_PORT)
    return session
        
def run_server(addr,port):
    global task
    log = Log(__name__,level='INFO')
    log.info('Run httpd server until ctrl-c input')
    def shutdown(task):
        task.worker.stop()
        task.running = False
    def start(httpd, id):
        httpd.start()
    def signal_handler(signum,stack):
        log.info('Sending shutdown to httpd server')
        thread.start_new_thread(shutdown, (task,)) 
    signal.signal(signal.SIGINT, signal_handler)
    server = Httpd(port=int(port),address=addr)
    task = WorkerThread(server,'httpd')
    worker = WorkerTasks(tasks=[task], func=start)
    worker.run()
    worker.wait_for_completion(timeout_sec=-1) # run forever
    