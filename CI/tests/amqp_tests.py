from config.amqp import *
from modules.amqp import Worker
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_is_not_none
from proboscis import SkipTest
from proboscis import test

LOG = Log(__name__)

@test(groups=['amqp.tests'])
class AMQPTests(object):

    def __init__(self):
        self.__task_worker = None

    @test(groups=['amqp.tests'],depends_on_groups=['check-obm'])
    def check_sel_task(self):
        """ Verify AMQP on.task.ipmi.sel.result """
        self.__task_worker = Worker(queue=QUEUE_SEL_RESULT,
                                    callbacks=[self.handle_sel_result])
        self.__task_worker.start()

    @test(groups=['amqp.tests'],depends_on_groups=['check-obm'])
    def check_sdr_task(self):
        """ Verify AMQP on.task.ipmi.sdr.result """
        self.__task_worker = Worker(queue=QUEUE_SDR_RESULT,
                                    callbacks=[self.handle_sdr_result])
        self.__task_worker.start()

    def handle_sel_result(self,body,message):
        LOG.debug(body)
        assert_is_not_none(body)
        assert_is_not_none(message)
        message.ack()
        self.__task_worker.stop()
        self.__task_worker = None
    
    def handle_sdr_result(self,body,message):
        LOG.debug(body)
        assert_is_not_none(body)
        assert_is_not_none(message)
        message.ack()
        self.__task_worker.stop()
        self.__task_worker = None


