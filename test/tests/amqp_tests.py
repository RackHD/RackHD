from config.amqp import *
from config.settings import *
from modules.amqp import Worker
from modules.logger import Log
from on_http import NodesApi as Nodes
from on_http import PollersApi as Pollers
from threading import Thread
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_is_not_none
from proboscis import SkipTest
from proboscis import test
from json import dumps,loads

LOG = Log(__name__)

@test(groups=['amqp.tests'])
class AMQPTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.__threadTasks = []

    class ThreadTask(object):
        def __init__(self,worker,thread,id):
            self.id = id
            self.worker = worker
            self.thread = thread
            self.state = False

    def amqp_tasker_thread(self,worker,id):
        LOG.info('spawning AMQP task thread for id {0}'.format(id))
        worker.start()

    def amqp_tasker_loop(self):
        completion = 0
        while completion < len(self.__threadTasks):
            for t in self.__threadTasks:
                if t.state is False:
                    LOG.info('shutting down worker thread for id {0}'.format(t.id))
                    t.thread.join()
                    completion += 1

    @test(groups=['amqp.tests.sel'],depends_on_groups=['check-obm'])
    def check_sel_task(self):
        """ Testing AMQP on.task.ipmi.sel.result """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        assert_equal(len(nodes),NODE_COUNT)
        self.__threadTasks = []
        for node in nodes:
            id = node.get('id')
            assert_not_equal(id,None)
            type = node.get('type')
            assert_not_equal(type,None)
            if type == 'compute':
                worker = Worker(queue=QUEUE_SEL_RESULT, callbacks=[self.handle_result])
                thread = Thread(target=self.amqp_tasker_thread,args=(worker,id,))
                thread.daemon = True
                self.__threadTasks.append(self.ThreadTask(worker,thread,id))
        for t in self.__threadTasks:
            t.thread.start()
            t.state = True
        self.amqp_tasker_loop()

    @test(groups=['amqp.tests.sdr'],depends_on_groups=['check-obm', 'amqp.tests.sel'])
    def check_sdr_task(self):
        """ Testing AMQP on.task.ipmi.sdr.result """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        assert_equal(len(nodes),NODE_COUNT)
        self.__threadTasks = []
        for node in nodes:
            id = node.get('id')
            assert_not_equal(id,None)
            type = node.get('type')
            assert_not_equal(type,None)
            if type == 'compute':
                worker = Worker(queue=QUEUE_SDR_RESULT, callbacks=[self.handle_result])
                thread = Thread(target=self.amqp_tasker_thread,args=(worker,id,))
                thread.daemon = True
                self.__threadTasks.append(self.ThreadTask(worker,thread,id))
        for t in self.__threadTasks:
            t.thread.start()
            t.state = True
        self.amqp_tasker_loop()

    @test(groups=['amqp.tests.chassis'],depends_on_groups=['check-obm', 'amqp.tests.sdr'])
    def check_chassis_task(self):
        """ Testing AMQP on.task.ipmi.chassis.result """
        Nodes().api1_1_nodes_get()
        nodes = loads(self.__client.last_response.data)
        assert_equal(len(nodes),NODE_COUNT)
        self.__threadTasks = []
        for node in nodes:
            id = node.get('id')
            assert_not_equal(id,None)
            type = node.get('type')
            assert_not_equal(type,None)
            if type == 'compute':
                worker = Worker(queue=QUEUE_CHASSIS_RESULT, callbacks=[self.handle_result])
                thread = Thread(target=self.amqp_tasker_thread,args=(worker,id,))
                thread.daemon = True
                self.__threadTasks.append(self.ThreadTask(worker,thread,id))
        for t in self.__threadTasks:
            t.thread.start()
            t.state = True
        self.amqp_tasker_loop()

    def handle_result(self,body,message):
        LOG.debug(body,json=True)
        assert_is_not_none(body)
        assert_is_not_none(message)
        id = body['value'].get('node')
        assert_not_equal(id,None)
        for t in self.__threadTasks:
            if t.id == id:
                workId = body['value'].get('workItemId')
                assert_not_equal(workId,None)
                Pollers().api1_1_pollers_identifier_get(workId)
                poller = loads(self.__client.last_response.data)
                config = poller.get('config')
                assert_not_equal(config,None)
                command = config.get('command')
                assert_not_equal(command,None)
                LOG.info('Received message (nodeId={0}, workId={1}, command={2})'.format(id,workId,command))
                message.ack()
                LOG.info('stopping AMQP worker for id {0}'.format(id))
                t.worker.stop()
                t.state = False

