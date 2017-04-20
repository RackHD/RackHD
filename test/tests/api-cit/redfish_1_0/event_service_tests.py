"""
Copyright (c) 2016-2017 Dell Inc. or its subsidiaries. All Rights Reserved.
"""
import fit_path  # NOQA: unused import                                                                                          
import unittest
import flogging
import thread

from config.redfish1_0_config import config
from config.settings import HTTPD_PORT
from on_http_redfish_1_0 import RedfishvApi as redfish
from modules.worker import WorkerThread, WorkerTasks
from modules.httpd import Httpd, BaseHandler, open_ssh_forward
from json import loads, dumps
from nosedep import depends
from nose.plugins.attrib import attr

logs = flogging.get_loggers()


# @test(groups=['redfish.event_service.tests'])
@attr(regression=True, smoke=True, event_service_rf1_tests=True)
class EventServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eventHandlerFailed = False

    def setUp(self):
        self.__client = config.api_client
        self.__client = config.api_client
        self.__httpd_port = 9995

    def __get_data(self):
        return loads(self.__client.last_response.data)

    def __httpd_start(self, worker, id):
        worker.start()

    class EventServiceHandler(BaseHandler):
        def do_POST(self):
            self.__class__.eventHandlerFailed = False
            self._set_headers()
            content_length = int(self.headers.getheader('content-length'), 0)
            body = loads(self.rfile.read(content_length))
            logs.info(dumps(body, indent=4))

            def shutdown(task):
                task.worker.stop()
                task.running = False
            thread.start_new_thread(shutdown, (task,))  # spawn thread to avoid deadlock
            if str(subscription.get('Id')) != str(body.get('MemberId')):
                # unittest does not catch the assertion inside a non-unittest class,
                # so setting class variable for the test to catch
                self.__class__.eventHandlerFailed = True
                logs.error("Subscription Id: %s does not match MemberId: %s",
                           str(subscription.get('Id')),
                           str(body.get('MemberId')))
                raise AssertionError("Subscription Id: {} does not match MemberId: {}".format(str(subscription.get('Id')),
                                                                                              str(body.get('MemberId'))))

    # @test(groups=['redfish.event_service_root'])
    def test_event_service_root(self):
        # """ Testing GET /EventService """
        redfish().event_service_root()
        status = self.__client.last_response.status
        self.assertEqual(200, status, msg='Expected 200 status, received status of {}'.format(status))

    @depends(after='test_event_service_root')
    def test_clean_up_subscriptions(self):
        # """ Delete any exising subscripts left over on old runs """
        redfish().get_events_collection()
        data = self.__get_data()
        for member in data.get('Members'):
            id = member.get('@odata.id').split('/redfish/v1/EventService/Subscriptions/')[1]
            redfish().delete_event(id)
            status = self.__client.last_response.status
            self.assertEqual(204, status, msg='Expected 204 status for DELETE, received status of {}'.format(status))
        redfish().get_events_collection()
        data = self.__get_data()
        self.assertEqual(len(data.get('Members')), 0, msg='unexpected subscription size, expected zero')

    # @test(groups=['redfish.create_subscription'], \
    #      depends_on_groups=['redfish.event_service_root'])
    @depends(after='test_clean_up_subscriptions')
    def test_create_event_subscription(self):
        # """ Testing POST /EventService/Subscription  """
        global subscription
        payload = {
            'Id': '12345',
            'Name': 'Alert 1',
            'Destination': 'http://localhost:{0}'.format(self.__httpd_port),
            'EventTypes': ['Alert'],
            'Context': 'Client Alerting',
            'Protocol': 'Redfish'
        }
        logs.info(" Post payload: ")
        logs.info(dumps(payload, indent=4))
        redfish().create_subscription(payload)
        subscription = self.__get_data()
        self.assertIsNotNone(subscription)
        logs.info(dumps(subscription, indent=4))
        status = self.__client.last_response.status
        self.assertEqual(201, status, msg='Expected 201 status, received status of {}'.format(status))

    # @test(groups=['redfish.subscriptions_collection'], \
    #      depends_on_groups=['redfish.create_subscription'])
    @depends(after='test_create_event_subscription')
    def test_get_event_subscription(self):
        # """ Testing GET /EventService/Subscription/:id  """
        redfish().get_event(subscription.get('Id'))
        data = self.__get_data()
        status = self.__client.last_response.status
        self.assertEqual(200, status, msg='Expected 200 status, received status of {}'.format(status))
        self.assertEqual(subscription.get('Id'), data.get('Id'),
                         msg='subscription id not found')

    # @test(groups=['redfish.submit_test_event'], \
    #      depends_on_groups=['redfish.create_subscription'])
    @depends(after='test_create_event_subscription')
    def test_submit_test_event(self):
        # """ Testing POST /EventService/SubmitTestEvent  """
        global task
        server = Httpd(port=int(HTTPD_PORT), handler_class=self.EventServiceHandler)
        task = WorkerThread(server, 'httpd')
        worker = WorkerTasks(tasks=[task], func=self.__httpd_start)
        worker.run()

        # forward port for services running on a guest host
        session = open_ssh_forward(self.__httpd_port)

        redfish().test_event(body={})
        worker.wait_for_completion(timeout_sec=60)
        session.logout()
        self.assertFalse(task.timeout, msg='timeout waiting for task {0}'.format(task.id))
        self.assertFalse(self.__class__.eventHandlerFailed, msg='Event handler reported subscriptionId / memberId mismatch')

    # @test(groups=['redfish.subscriptions_collection'], \
    #      depends_on_groups=['redfish.submit_test_event'])
    @depends(after='test_submit_test_event')
    def test_subscription_collection(self):
        # """ Testing GET /EventService/Subscription  """
        redfish().get_events_collection()
        data = self.__get_data()
        status = self.__client.last_response.status
        self.assertEqual(200, status, msg='Expected 200 status for GET, received status of {}'.format(status))
        ids = []
        for member in data.get('Members'):
            ids.append(member.get('@odata.id').split('/redfish/v1/EventService/Subscriptions/')[1])
        self.assertTrue(subscription.get('Id') in ids, msg='subscription id not found')

    # @test(groups=['redfish.delete_subscriptions'], \
    #      depends_on_groups=['redfish.subscriptions_collection'])
    @depends(after='test_subscription_collection')
    def test_delete_subscriptions(self):
        # """ Testing DELETE /EventService/Subscription  """
        redfish().get_events_collection()
        data = self.__get_data()
        for member in data.get('Members'):
            id = member.get('@odata.id').split('/redfish/v1/EventService/Subscriptions/')[1]
            redfish().delete_event(id)
            status = self.__client.last_response.status
            self.assertEqual(204, status, msg='Expected 204 status for DELETE, received status of {}'.format(status))
        redfish().get_events_collection()
        data = self.__get_data()
        self.assertEqual(len(data.get('Members')), 0, msg='unexpected subscription size, expected zero')
