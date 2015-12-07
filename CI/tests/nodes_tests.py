from config.settings import *
from modules.nodes import Nodes
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test

LOG = Log(__name__)

@test(groups=['nodes.tests'])
class NodesTests(object):

    def __init__(self):
        pass

    @test(groups=['nodes.test','check-nodes'])
    def check_nodes(self):
        """ Verify GET:/nodes API """
        rsp = Nodes().get_nodes()
        assert_equal(200,rsp.status_code)
        assert_not_equal(len(rsp.json()), 0, message='Node list was empty!')
        rsp = Nodes().get_nodes(uid='fooey')
        assert_equal(404,rsp.status_code)

