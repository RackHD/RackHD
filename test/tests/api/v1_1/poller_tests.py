from config.api1_1_config import *
from config.amqp import *
from modules.logger import Log
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import PollersApi as Pollers
from on_http_api1_1 import TemplatesApi as Templates
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis import SkipTest
from proboscis import test
from json import loads
import time

LOG = Log(__name__)

@test(groups=['poller.tests'])
class PollerTests(object):

    def __init__(self):
        self.__client = config.api_client

    @test(groups=['test-node-poller'], depends_on_groups=['test-nodes'])
    def test_node_pollers(self):
        """ Test /nodes/:id/pollers are running """
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        LOG.debug(nodes, json=True)
        samples = []
        valid = False

        for n in nodes:
            LOG.info(n)
            if n.get('type') == 'compute':
                uuid = n.get('id')
                Nodes().nodes_identifier_pollers_get(uuid)
                rsp = self.__client.last_response
                data = loads(rsp.data)
                assert_equal(200, rsp.status, message=rsp.reason)
                assert_not_equal(0, len(data), \
                        message='Failed to find poller for nodes {0}'.format(n.get('id')))
                samples.append(data[0])

        for sample in samples:
            count = 18 # Wait for 3 mins (poller interval is 1 min)
            while valid == False:
                try:
                    Templates().pollers_identifier_data_get(sample.get('id'))
                    valid = True
                except Exception, e:
                    LOG.warning('Poller {0} doesn\'t work normally'.format(sample.get('id')))
                    time.sleep(10)
                    count -= 1
                    assert_not_equal(0, count, \
                            message='Poller {0} failed to get data'.format(sample.get('id')))
