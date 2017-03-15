"""
Copyright (c) 2017 Dell Inc. or its subsidiaries. All Rights Reserved.

A set of super-simple matchers to use to self-test the matching framework.
"""
import sys
import time
import optparse
import uuid
import gevent
import gevent.queue
from .monitor_abc import StreamMonitorBaseClass
from .stream_matchers_base import StreamMatchBase
from .amqp_od import RackHDAMQPOnDemand
from kombu import Connection, Producer, Queue, Exchange, Consumer


class _AMQPServerWrapper(object):
    def __init__(self, amqp_url):
        self.__connection = Connection(amqp_url)
        self.__connection.connect()
        self.__monitors = {}
        self.__running = True
        self.__consumer = Consumer(self.__connection, on_message=self.__on_message)
        self.__consumer_gl = gevent.spawn(self.__consumer_greenlet_main)

    def __consumer_greenlet_main(self):
        gevent.sleep(0)
        while self.__running:
            self.__consumer.consume()
            try:
                self.__connection.drain_events(timeout=0.1)
            except Exception as ex:
                # print("was woken because {}".format(ex))
                pass
            gevent.sleep(0)
            # print("---loop")

    def __on_message(self, msg):
        ct = msg.delivery_info['consumer_tag']
        assert ct in self.__monitors, \
            "Message from consumer '{}', but we are not monitoring that (list={})".format(
                msg.delivery_info['consumer_tag'], self.__monitors.keys())
        mon = self.__monitors[ct]
        mon['event_cb'](msg, msg.body)

    @property
    def connected(self):
        return self.__connection.connected

    def create_add_monitor(self, exchange, routing_key, event_cb, queue_name=None):
        mname = "ex={} rk={} qn={}".format(exchange, routing_key, queue_name)
        if mname in self.__monitors:
            mon = self.__monitors[mname]
            mon["event_cb"] = event_cb
        else:
            if queue_name is None:
                queue_name = ''
                exclusive = True
            else:
                exclusive = False
            ex = Exchange(exchange, 'topic')
            queue = Queue(exchange=ex, routing_key=routing_key, exclusive=exclusive)
            bound_queue = queue.bind(self.__connection)
            self.__consumer.add_queue(bound_queue)
            bound_queue.consume(mname, self.__on_message)
            mon = {
                "event_cb": event_cb,
                "exchange": ex
                }
            self.__monitors[mname] = mon
        return mon['exchange']

    def inject(self, exchange, routing_key, payload):
        prod = Producer(self.__connection, exchange=exchange, routing_key=routing_key)
        prod.publish(payload)

    def test_helper_sync_send_msg(self, exchange, ex_rk, send_rk, payload):
        ex = Exchange(exchange, 'topic')
        queue = Queue(exchange=ex, routing_key=ex_rk + '.*', exclusive=True, channel=self.__connection)
        queue.declare()
        prod = Producer(self.__connection, exchange=ex, routing_key=send_rk)
        prod.publish(payload)
        return queue

    def test_helper_sync_recv_msg(self, queue):
        for tick in range(10):
            msg = queue.get()
            if msg is not None:
                break
            time.sleep(1)
        return msg


class _AMQPMatcher(StreamMatchBase):
    """
    Implementation of a StreamMatchBase matcher.
    """
    def __init__(self, match_tbd, description, min=1, max=1):
        self.__match_tbd = match_tbd
        super(_AMQPMatcher, self).__init__(description, min=min, max=max)

    def _match(self, other_event):
        return bool(other_event)

    def dump(self, ofile=sys.stdout, indent=0):
        super(_AMQPMatcher, self).dump(ofile=ofile, indent=indent)
        ins = ' ' * indent
        print >>ofile, "{0} match_tbd='{1}'".format(ins, self.__match_tbd)


class _AMQPQueueMonitor(StreamMonitorBaseClass):
    def __init__(self, amqp_server, exchange, routing_key, queue_name=None):
        super(_AMQPQueueMonitor, self).__init__()
        # let base class catch up with us statewise (we get created from
        # inside the entire amqp-stream-monitor after begin). We do this here
        # so that nothing can wander in as the queues are set up, etc.
        self.handle_begin()
        self.__server = amqp_server
        self.__routing_key = routing_key
        self.__saved_messages = gevent.queue.Queue()

        ex = self.__server.create_add_monitor(exchange, routing_key, self.__got_one_cb)
        self.__exchange = ex

    def __got_one_cb(self, msg, body):
        self.__saved_messages.put([msg, body])

    def inject_test(self):
        payload = {'test_uuid': str(uuid.uuid4())}
        self.__server.inject(self.__exchange, self.__routing_key, payload)
        what_sent = {'route_key': self.__routing_key, 'payload': payload}
        return what_sent

    def wait_for_one_message(self, timeout=5):
        sleep_till = time.time() + timeout
        found = False
        tries = 0
        while time.time() < sleep_till:
            try:
                tries += 1
                msg, body = self.__saved_messages.get(block=False)
                found = True
            except gevent.queue.Empty:
                pass
            if found:
                return msg, body
            gevent.sleep(0)
        return None, None


class AMQPStreamMonitor(StreamMonitorBaseClass):
    """
    Implementation of a StreamMonitorBaseClass that handles working with AMQP.

    Needs to be able to:
    * Create an AMQP-on-demand server if asked
    * Spin up an AMQP receiver greenlet to on-demand
    """
    def handle_begin(self):
        """
        Handles plugin 'begin' event. This means spinning up
        a greenlet to monitor the AMQP server.
        """
        super(AMQPStreamMonitor, self).handle_begin()
        self.__monitors = []
        sm_amqp_url = getattr(self.__options, 'sm_amqp_url', None)
        if sm_amqp_url is None:
            self.__amqp_on_demand = RackHDAMQPOnDemand()
            sm_amqp_url = self.__amqp_on_demand.get_url()
        else:
            self.__amqp_on_demand = None
        self.__amqp_server = _AMQPServerWrapper(sm_amqp_url)

    def test_helper_is_amqp_running(self):
        return self.__amqp_server.connected

    def test_helper_sync_send_msg(self, exchange, ex_rk, send_rk, payload):
        return self.__amqp_server.test_helper_sync_send_msg(
            exchange, ex_rk, send_rk, payload)

    def test_helper_sync_recv_msg(self, queue):
        return self.__amqp_server.test_helper_sync_recv_msg(queue)

    def get_queue_monitor(self, exchange, routing_key, queue_name=None):
        assert queue_name is None, \
            'named queues coming in another story. param is for api definition only currently'
        monitor = _AMQPQueueMonitor(self.__amqp_server, exchange, routing_key)
        self.__monitors.append(monitor)

        return monitor

    @classmethod
    def enabled_for_nose(true):
        return True

    def set_options(self, options):
        self.__options = options

    @classmethod
    def add_nose_parser_opts(self, parser):
        amqp_group = optparse.OptionGroup(parser, 'AMQP options')
        parser.add_option_group(amqp_group)
        amqp_group.add_option(
            '--sm-amqp-url', dest='sm_amqp_url', default=None,
            help="set the AMQP url to use. If not set, a docker based server will be setup and used")
