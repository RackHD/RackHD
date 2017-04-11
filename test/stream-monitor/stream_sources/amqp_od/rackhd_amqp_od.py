from amqp_on_demand import AMQPOnDemand
from kombu import Exchange, Connection, Queue


class RackHDAMQPOnDemand(AMQPOnDemand):
    def __init__(self):
        super(RackHDAMQPOnDemand, self).__init__()

        self.__setup_rackhd_style_amqp()

    def __setup_rackhd_style_amqp(self):
        """
        Need to make exchanges and named queus to make this
        look like a RackHD instance amqp.
        """
        con = Connection(hostname=self.host, port=self.ssl_port, ssl=False)
        on_task = self.__assure_exchange(con, 'on.task', 'topic')
        self.__assure_named_queue(con, on_task, 'ipmi.command.sel.result')
        self.__assure_named_queue(con, on_task, 'ipmi.command.sdr.result')
        self.__assure_named_queue(con, on_task, 'ipmi.command.chassis.result')

        on_events = self.__assure_exchange(con, 'on.events', 'topic')
        self.__assure_named_queue(con, on_events, 'graph.finished')
        self.__assure_named_queue(con, on_events, 'polleralert.sel.updated', '#')

        self.__assure_exchange(con, 'on.heartbeat', 'topic')

    def __assure_exchange(self, connection, exchange_name, exchange_type):
        exchange = Exchange(exchange_name, type=exchange_type)
        bound_exchange = exchange(connection)
        bound_exchange.declare()

    def __assure_named_queue(self, connection, exchange, queue_name, routing_key_extension='*'):
        routing_key = '{}.{}'.format(queue_name, routing_key_extension)
        queue = Queue(queue_name, exchange, routing_key, connection)
        queue.declare()

    def get_url(self):
        return 'amqp://{}:{}'.format(self.host, self.ssl_port)
