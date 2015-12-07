from config.settings import *
from config.amqp import *
from logger import Log
from json import dumps, loads
from threading import Thread
from kombu.mixins import ConsumerMixin
from kombu import BrokerConnection

LOG = Log('kombu')

class Worker(ConsumerMixin):
    def __init__(self, **kwargs):
        self.__callbacks = kwargs.get('callbacks',self.on_message)
        self.__amqp_url = kwargs.get('amqp_url',AMQP_URL)
        self.__queue = kwargs.get('queue')
        if self.__queue is None:
            raise TypeError('invalid worker queue parameter')
        self.connection = BrokerConnection(self.__amqp_url)
    
    def get_consumers(self, consumer, channel):
        if not isinstance(self.__callbacks,list):
            self.__callbacks = [ self.__callbacks ]
        return [consumer(self.__queue, callbacks=self.__callbacks)]

    def on_message(self, body, message):
        out =  'Received message: %r' % dumps(body)
        out += ' properties: %s' % dumps(message.properties)
        out += '  delivery_info: %s' % dumps(message.delivery_info)
        LOG.info(out,pprint=True)
        message.ack()

    def start(self):
        LOG.info('Starting AMQP worker {0}'.format(self.__queue))
        self.run()

    def stop(self):
        LOG.info('Stopping AMQP worker {0}'.format(self.__queue))
        self.should_stop = True        


