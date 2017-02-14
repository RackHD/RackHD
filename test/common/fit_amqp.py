'''
Copyright 2017 Dell Inc. or its subsidiaries.  All Rights Reserved.
Author(s):
Norton Luo

'''
import threading, pika, logging
import fit_common


class AMQP_worker(threading.Thread):
    '''
    This AMQP worker Class will creat another thread when initialized and runs asynchronously.
    The externalcallback is the callback function entrance for user.
    The callback function will be call when AMQP message is received.
    Each test case can define its own callback and pass the function name to the AMQP class.
    The timeout parameter specify how long the AMQP daemon will run. self.panic is called when timeout.
    eg:
    def callback(self, ch, method, properties, body):
        print(" [x] %r:%r" % (method.routing_key, body))

    td = fit_amqp.AMQP_worker("node.added.#", callback)
    td.setDaemon(True)
    td.start()
    '''

    def __init__(self, exchange_name, routing_key, externalcallback, timeout=10):
        threading.Thread.__init__(self)
        pika_logger = logging.getLogger('pika')
        if fit_common.VERBOSITY >= 8:
            pika_logger.setLevel(logging.DEBUG)
        elif fit_common.VERBOSITY >= 4:
            pika_logger.setLevel(logging.WARNING)
        else:
            pika_logger.setLevel(logging.ERROR)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=fit_common.fitargs()["ora"], port=fit_common.fitports()['amqp']))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(
            exchange=exchange_name,
            queue=queue_name,
            routing_key=routing_key)
        self.channel.basic_consume(externalcallback, queue=queue_name)
        self.connection.add_timeout(timeout, self.panic)

    def panic(self):
        self.channel.stop_consuming()
        if fit_common.VERBOSITY >= 4:
            print "Pika connection timeout"
        self.connection.close()
        exit(0)

    def run(self):
        if fit_common.VERBOSITY >= 4:
            print 'start consuming'
        self.channel.start_consuming()