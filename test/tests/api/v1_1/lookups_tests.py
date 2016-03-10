from config.api1_1_config import *
from on_http_api1_1 import LookupsApi as Lookups
from on_http_api1_1 import NodesApi as Nodes
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_is_not_none
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)

@test(groups=['lookups.tests'])
class LookupsTests(object):

    def __init__(self):
        self.__client = config.api_client
        self.lookup =   {
                            "ipAddress": "11.11.11.11",
                            "macAddress": "ae:aa:aa:aa:aa:aa",
                            "node":"456"
                        }
        self.id = ""
        self.patchedNode= {"node": "666" }

    @test(groups=['lookups.tests', 'check-lookups-query'], depends_on_groups=['nodes.tests'])
    def check_lookups_query(self):
        """ Testing GET:/lookups?q=term """
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        assert_not_equal(0, len(nodes), message='Node list was empty!')
        obms = [ n.get('obmSettings') for n in nodes if n.get('obmSettings') is not None ]
        hosts = []
        for o in obms:
            for c in o:
                hosts.append(c.get('config').get('host'))
        assert_not_equal(0, len(hosts), message='No OBM hosts were found!')
        for host in hosts:
            Lookups().lookups_get(q=host)
            rsp = self.__client.last_response
            assert_equal(200, rsp.status, message=rsp.reason)
            assert_not_equal(0, len(rsp.data))

    @test(groups=['check-lookup-id'],depends_on_groups=['check-lookups-query'])
    def check_lookup_id(self):
        """ Testing GET:/lookups/:id """
        Nodes().nodes_get()
        nodes = loads(self.__client.last_response.data)
        assert_not_equal(0, len(nodes), message='Node list was empty!')
        obms = [ n.get('obmSettings') for n in nodes if n.get('obmSettings') is not None ]
        assert_not_equal(0, len(obms), message='No OBM settings found!')
        entries = []
        for obm in obms:
            for cfg in obm:
                host = cfg.get('config').get('host')
                Lookups().lookups_get(q=host)
                list = loads(self.__client.last_response.data)
                entries.append(list)

        assert_not_equal(0, len(entries), message='No lookup entries found!')
        for entry in entries:
            for id in entry:
                Lookups().lookups_id_get(id.get('id'))
                rsp = self.__client.last_response
                assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['check-post-lookup'],depends_on_groups=['check-lookups-query'])
    def post_lookup(self):
        """ Testing POST /"""

        #Validate that the lookup has not been posted from a previous test
        Lookups().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        listLen =len(rsp)
        for i, val in enumerate (rsp):
            if ( self.lookup.get("macAddress") ==  str (rsp[i].get('macAddress'))  ):
                    LOG.info("Deleting the lookup with the same info before we post again")
                    deleteID= str (rsp[i].get('id'))
                    Lookups().lookups_id_delete(deleteID)


        #Add a lookup
        Lookups().lookups_post(self.lookup)
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)
        self.id = str (loads(rsp.data).get('id'))
        LOG.info("ID is "+ self.id)

        #Validate the content
        Lookups().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        assert_equal(str(rsp[0].get("ipAddress")),str(self.lookup.get("ipAddress")))
        assert_equal(str(rsp[0].get("macAddress")),str(self.lookup.get("macAddress")))
        assert_equal(str(rsp[0].get("node")),str(self.lookup.get("node")))

    @test(groups=['check-post-lookup-negativeTesting'],depends_on_groups=['check-lookups-query','check-post-lookup'])
    def post_lookup_negativeTesting(self):
        """ Negative Testing POST / """
        #Validate that a POST for a lookup with same id as an existing one gets rejected
        try:
            Lookups().lookups_post(self.lookup)
        except Exception,e:
           assert_equal(400,e.status, message = 'status should be 400')

    @test(groups=['check-patch-lookup'],depends_on_groups=['check-lookups-query','check-post-lookup','check-post-lookup-negativeTesting'])
    def patch_lookup(self):
        """ Testing PATCH /:id"""
        Lookups().lookups_id_patch(self.id,body=self.patchedNode)

        #validate that the node element has been updated
        Lookups().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        assert_equal(str(rsp[0].get("node")),self.patchedNode.get("node") )

    @test(groups=['check-delete-lookup'], depends_on_groups=['check-lookups-query','check-post-lookup','check-patch-lookup'])
    def delete_lookup(self):
        """ Testing DELETE /:id """
        #Validate that the lookup is there before it is deleted
        Lookups().lookups_id_get(self.id)
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)

        #delete the lookup
        LOG.info("The lookup ID to be deleted is "+ self.id)
        Lookups().lookups_id_delete(self.id)
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)

        #Validate that the lookup has been deleted and the returned value is an empty list
        try:
            Lookups().lookups_id_get(self.id)
        except Exception,e:
           assert_equal(404,e.status)
