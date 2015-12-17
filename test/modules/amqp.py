from config.settings import *
from config.amqp import *
from logger import Log
from json import dumps, loads
from threading import Thread
from kombu.mixins import ConsumerMixin
from kombu import BrokerConnection

LOG = Log('kombu')

"""
Class to abstract AMQP consumer event handling
:param callbacks: optional callbacks to be invoked on queue event
:param amqp_url: optional AMQP URL to connect, defaults from config/amqp.py
:param queue: The queue exchange to listen on for events
"""
class Worker(ConsumerMixin):
    def __init__(self, **kwargs):
        self.__callbacks = kwargs.get('callbacks',self.on_message)
        self.__amqp_url = kwargs.get('amqp_url',AMQP_URL)
        self.__queue = kwargs.get('queue')
        self.__conn_retries = kwargs.get('max_retries',2)
        if self.__queue is None:
            raise TypeError('invalid worker queue parameter')
        self.connection = BrokerConnection(self.__amqp_url)
        self.connection.ensure_connection(max_retries=self.__conn_retries, callback=self.on_conn_retry)
    
    def get_consumers(self, consumer, channel):
        if not isinstance(self.__callbacks,list):
            self.__callbacks = [ self.__callbacks ]
        return [consumer(self.__queue, callbacks=self.__callbacks)]

    def on_message(self, body, message):
        out =  'Received message: %r' % dumps(body)
        out += ' properties: %s' % dumps(message.properties)
        out += '  delivery_info: %s' % dumps(message.delivery_info)
        LOG.info(out,json=True)
        message.ack()

    def on_conn_retry(self):
        LOG.error('Retrying connection for {0}'.format(self.__amqp_url))

    def start(self):
        LOG.info('Starting AMQP worker {0}'.format(self.__queue))
        self.run()

    def stop(self):
        LOG.info('Stopping AMQP worker {0}'.format(self.__queue))
        self.should_stop = True        


