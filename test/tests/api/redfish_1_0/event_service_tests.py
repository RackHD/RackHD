from config.redfish1_0_config import *
from config.settings import *
from on_http_redfish_1_0 import RedfishvApi as redfish
from modules.httpd import Httpd, BaseHandler, open_ssh_forward
from modules.logger import Log
from modules.worker import WorkerThread, WorkerTasks
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from json import loads
import thread

LOG = Log(__name__)

@test(groups=['redfish.event_service.tests'])
class EventServiceTests(object):
    def __init__(self):
        self.__client = config.api_client
        self.__httpd_port = 9995
        
    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __httpd_start(self,worker,id):
        worker.start()

    class EventServiceHandler(BaseHandler):
        def do_POST(self):
            self._set_headers()
            content_length = int(self.headers.getheader('content-length'),0)
            body = loads(self.rfile.read(content_length))
            LOG.info(body,json=True)
            def shutdown(task):
                task.worker.stop()
                task.running = False
            thread.start_new_thread(shutdown, (task,)) # spawn thread to avoid deadlock
            assert_equal(subscription.get('Id'), body.get('MemberId'))
    
    @test(groups=['redfish.event_service_root'])
    def test_event_service_root(self):
        """ Testing GET /EventService """
        redfish().event_service_root()
        data = self.__get_data()
        status = self.__client.last_response.status
        assert_equal(200, status, message='unexpected status')
    
    @test(groups=['redfish.create_subscription'], \
          depends_on_groups=['redfish.event_service_root'])
    def test_create_event_subscription(self):
        """ Testing POST /EventService/Subscription  """
        global subscription 
        payload = { 
            'Destination': 'http://localhost:{0}'.format(self.__httpd_port), 
            'EventTypes': ['Alert'], 
            'Context': 'Client Alerting', 
            'Protocol': 'Redfish' 
        }
        redfish().create_subscription(payload)
        subscription = self.__get_data()
        assert_is_not_none(subscription)
        LOG.info(subscription,json=True)
        status = self.__client.last_response.status
        assert_equal(201, status, message='unexpected status on create')
        
    @test(groups=['redfish.subscriptions_collection'], \
          depends_on_groups=['redfish.create_subscription'])
    def test_get_event_subscription(self):
        """ Testing GET /EventService/Subscription/:id  """
        redfish().get_event(subscription.get('Id'))
        data = self.__get_data()
        status = self.__client.last_response.status
        assert_equal(200, status, message='unexpected status')
        assert_equal(subscription.get('Id'), data.get('Id'), \
            message='subscription id not found')
        
    @test(groups=['redfish.submit_test_event'], \
          depends_on_groups=['redfish.create_subscription'])
    def test_submit_test_event(self):
        """ Testing POST /EventService/SubmitTestEvent  """
        global task
        server = Httpd(port=int(HTTPD_PORT), handler_class=self.EventServiceHandler)
        task = WorkerThread(server,'httpd')
        worker = WorkerTasks(tasks=[task], func=self.__httpd_start)
        worker.run()
        
        # forward port for services running on a guest host
        session = open_ssh_forward(self.__httpd_port) 
        
        redfish().test_event(body={})
        worker.wait_for_completion(timeout_sec=60)
        session.logout()
        assert_false(task.timeout, message='timeout waiting for task {0}'.format(task.id))
   
    @test(groups=['redfish.subscriptions_collection'], \
          depends_on_groups=['redfish.submit_test_event'])
    def test_subscription_collection(self):
        """ Testing GET /EventService/Subscription  """
        redfish().get_events_collection()
        data = self.__get_data()
        status = self.__client.last_response.status
        assert_equal(200, status, message='unexpected status on GET')
        ids = []
        for member in data.get('Members'):
            ids.append(member.get('@odata.id') \
                .split('/redfish/v1/EventService/Subscriptions/')[1])
        assert_true(subscription.get('Id') in ids, message='subscription id not found')
        
    @test(groups=['redfish.delete_subscriptions'], \
          depends_on_groups=['redfish.subscriptions_collection'])
    def test_delete_subscriptions(self):
        """ Testing DELETE /EventService/Subscription  """
        redfish().get_events_collection()
        data = self.__get_data()
        for member in data.get('Members'):
            id = member.get('@odata.id').split('/redfish/v1/EventService/Subscriptions/')[1]
            redfish().delete_event(id)
            status = self.__client.last_response.status
            assert_equal(200, status, message='unexpected status on DELETE')
        redfish().get_events_collection()
        data = self.__get_data()
        assert_equal(len(data.get('Members')), 0, message='unexpected subscription size, expected zero')