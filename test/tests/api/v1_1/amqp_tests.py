from config.amqp import *
from config.api1_1_config import *
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
from modules.logger import Log
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import PollersApi as Pollers
from threading import Thread
from datetime import datetime
from proboscis.asserts import assert_is_not_none
from proboscis import SkipTest
from proboscis import test
from json import dumps,loads

LOG = Log(__name__)

@test(groups=['amqp.tests'])
class AMQPTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__tasks = []

    def __task_thread(self,worker,id):
        LOG.info('starting AMQP worker for id {0}'.format(id))
        worker.start()
        
    def __handle_result(self,body,message):
        LOG.debug(body,json=True)
        assert_is_not_none(body)
        assert_is_not_none(message)
        id = body['value'].get('node')
        assert_is_not_none(id)
        for task in self.__tasks:
            if task.id == id:
                workId = body['value'].get('workItemId')
                assert_is_not_none(workId)
                Pollers().pollers_identifier_get(workId)
                poller = loads(self.__client.last_response.data)
                config = poller.get('config')
                assert_is_not_none(config)
                command = config.get('command')
                assert_is_not_none(command)
                LOG.info('Received message (nodeId={0}, workId={1}, command={2})' \
					.format(id,workId,command))
                message.ack()
                task.worker.stop()
                task.running = False

    @test(groups=['amqp.tests.sel'], \
          depends_on_groups=['check-obm'])
    def check_sel_task(self):
        """ Testing AMQP on.task.ipmi.sel.result """
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        self.__tasks = []
        for node in nodes:
            id = node.get('id')
            assert_is_not_none(id)
            type = node.get('type')
            assert_is_not_none(type)
            if type == 'compute':
                worker = AMQPWorker(queue=QUEUE_SEL_RESULT, \
                                    callbacks=[self.__handle_result])
                self.__tasks.append(WorkerThread(worker,id))
        tasks = WorkerTasks(tasks=self.__tasks, func=self.__task_thread)
        tasks.run()
        tasks.wait_for_completion()

    @test(groups=['amqp.tests.sdr'], \
          depends_on_groups=['amqp.tests.sel'])
    def check_sdr_task(self):
        """ Testing AMQP on.task.ipmi.sdr.result """
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        self.__tasks = []
        for node in nodes:
            id = node.get('id')
            assert_is_not_none(id)
            type = node.get('type')
            assert_is_not_none(type)
            if type == 'compute':
                worker = AMQPWorker(queue=QUEUE_SDR_RESULT, \
                                    callbacks=[self.__handle_result])
                self.__tasks.append(WorkerThread(worker,id))
        tasks = WorkerTasks(tasks=self.__tasks, func=self.__task_thread)
        tasks.run()
        tasks.wait_for_completion()
        
    @test(groups=['amqp.tests.chassis'], \
          depends_on_groups=['amqp.tests.sdr'])
    def check_chassis_task(self):
        """ Testing AMQP on.task.ipmi.chassis.result """
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        self.__tasks = []
        for node in nodes:
            id = node.get('id')
            assert_is_not_none(id)
            type = node.get('type')
            assert_is_not_none(type)
            if type == 'compute':
                worker = AMQPWorker(queue=QUEUE_CHASSIS_RESULT, \
                                    callbacks=[self.__handle_result])
                self.__tasks.append(WorkerThread(worker,id))
        tasks = WorkerTasks(tasks=self.__tasks, func=self.__task_thread)
        tasks.run()
        tasks.wait_for_completion()
