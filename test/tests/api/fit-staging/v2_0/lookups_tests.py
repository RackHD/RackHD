from config.api2_0_config import config as config_new
from on_http_api2_0 import ApiApi as Api
from on_http_api2_0.rest import ApiException
from modules.logger import Log
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

@test(groups=['lookups_api2.tests'])
class LookupsTests(object):

    def __init__(self):
        self.__client = config_new.api_client
        self.lookup =   {
                            "ipAddress": "11.11.11.11",
                            "macAddress": "ae:aa:aa:aa:aa:aa",
                            "node":"456"
                        }
        self.id = ""
        self.patchedNode= {"node": "666" }

    @test(groups=['lookups_api2.tests', 'api2_check-lookups'], depends_on_groups=['obm_api2.tests'])
    def check_lookups(self):
        """ Testing GET:/lookups """
        Api().lookups_get()
        rsp = self.__client.last_response
        LOG.info("\nLookup list: {}\n".format(rsp.data, json=True))
        assert_equal(200, rsp.status, message=rsp.reason)
        assert_not_equal(0, len(rsp.data))

    @test(groups=['api2_check-lookups-query'], depends_on_groups=['api2_check-lookups'])
    def check_lookups_query(self):
        """ Testing GET:/lookups?q=term """
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        assert_not_equal(0, len(nodes), message='Node list was empty!')
        Api().obms_get()
        obms = loads(self.__client.last_response.data)
        LOG.info("OBM get data: {}".format(obms, json=True))
        hosts = []
        for o in obms:
            hosts.append(o.get('config').get('host'))
        assert_not_equal(0, len(hosts), message='No OBM hosts were found!')
        LOG.info("Hosts {}".format(hosts, json=True))
        for host in hosts:
            LOG.info("Looking up host: {}".format(host))
            Api().lookups_get(q=host)
            rsp = self.__client.last_response
            assert_equal(200, rsp.status, message=rsp.reason)
            assert_not_equal(0, len(rsp.data))

    @test(groups=['api2_check-lookup-id'],depends_on_groups=['api2_check-lookups-query'])
    def check_lookup_id(self):
        """ Testing GET:/lookups/:id """
        Api().nodes_get_all()
        nodes = loads(self.__client.last_response.data)
        assert_not_equal(0, len(nodes), message='Node list was empty!')
        Api().obms_get()
        obms = loads(self.__client.last_response.data)
        assert_not_equal(0, len(obms), message='No OBM settings found!')
        entries = []
        for obm in obms:
            host = obm.get('config').get('host')
            Api().lookups_get(q=host)
            list = loads(self.__client.last_response.data)
            entries.append(list)

        assert_not_equal(0, len(entries), message='No lookup entries found!')
        for entry in entries:
            for id in entry:
                Api().lookups_get_by_id(id.get('id'))
                rsp = self.__client.last_response
                assert_equal(200, rsp.status, message=rsp.reason)

    @test(groups=['api2_check-post-lookup'],depends_on_groups=['api2_check-lookups-query'])
    def post_lookup(self):
        """ Testing POST /"""

        #Validate that the lookup has not been posted from a previous test
        Api().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        listLen =len(rsp)
        for i, val in enumerate (rsp):
            if ( self.lookup.get("macAddress") ==  str (rsp[i].get('macAddress'))  ):
                    LOG.info("Deleting the lookup with the same info before we post again")
                    deleteID= str (rsp[i].get('id'))
                    Api().lookups_del_by_id(deleteID)


        #Add a lookup
        Api().lookups_post(self.lookup)
        rsp = self.__client.last_response
        assert_equal(201, rsp.status, message=rsp.reason)
        self.id = str (loads(rsp.data).get('id'))
        LOG.info("ID is "+ self.id)

        #Validate the content
        Api().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        assert_equal(str(rsp[0].get("ipAddress")),str(self.lookup.get("ipAddress")))
        assert_equal(str(rsp[0].get("macAddress")),str(self.lookup.get("macAddress")))
        assert_equal(str(rsp[0].get("node")),str(self.lookup.get("node")))

    @test(groups=['api2_check-post-lookup-negativeTesting'],depends_on_groups=['api2_check-lookups-query','api2_check-post-lookup'])
    def post_lookup_negativeTesting(self):
        """ Negative Testing POST / """
        #Validate that a POST for a lookup with same id as an existing one gets rejected
        try:
            Api().lookups_post(self.lookup)
        except ApiException as e:
           assert_equal(400, e.status, message = 'status should be 400')
        except (TypeError, ValueError) as e:
           assert(e.message)

    @test(groups=['api2_check-patch-lookup'],depends_on_groups=['api2_check-lookups-query','api2_check-post-lookup','api2_check-post-lookup-negativeTesting'])
    def patch_lookup(self):
        """ Testing PATCH /:id"""
        Api().lookups_patch_by_id(self.id, self.patchedNode)

        #validate that the node element has been updated
        Api().lookups_get(q=self.lookup.get("macAddress"))
        rsp = loads(self.__client.last_response.data)
        assert_equal(str(rsp[0].get("node")),self.patchedNode.get("node") )

    @test(groups=['check-delete-lookup'], depends_on_groups=['api2_check-lookups-query','api2_check-post-lookup','api2_check-patch-lookup'])
    def delete_lookup(self):
        """ Testing DELETE /:id """
        #Validate that the lookup is there before it is deleted
        Api().lookups_get_by_id(self.id)
        rsp = self.__client.last_response
        assert_equal(200, rsp.status, message=rsp.reason)

        #delete the lookup
        LOG.info("The lookup ID to be deleted is "+ self.id)
        Api().lookups_del_by_id(self.id)
        rsp = self.__client.last_response
        assert_equal(204, rsp.status, message=rsp.reason)

        #Validate that the lookup has been deleted and the returned value is an empty list
        try:
            Api().lookups_get_by_id(self.id)
        except ApiException as e:
           assert_equal(404, e.status, message = 'status should be 404')
        except (TypeError, ValueError) as e:
           assert(e.message)
