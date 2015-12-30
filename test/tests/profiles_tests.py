
import json
from config.settings import *
from on_http import ProfilesApi as Profiles
from on_http import rest
from modules.logger import Log
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_true
from proboscis import SkipTest
from proboscis import test
from json import dumps, loads

LOG = Log(__name__)



@test(groups=['profiles.tests'])
class ProfilesTests(object):

    addedDict= {'name':'Fih', 'contents': "what an amazing thing"}


    def __init__(self):
        self.__client = config.api_client
        self.addedName = "ProfileName_1"
        self.addedContents = "Random Content"


    @test(groups=['profiles.tests', 'profile_library_get'])
    def test_profiles_library_get(self):
        """ Testing GET:/library"""
        Profiles().api1_1_profiles_library_get()
        assert_equal(200,self.__client.last_response.status)
        assert_not_equal(0, len(json.loads(self.__client.last_response.data)), message='Profile list was empty!')

    @test(groups=['profile_library_put'], depends_on_groups=['profile_library_get'])
    def test_profiles_put(self):
        """ Testing PUT:/nodes """
        #Get the number of profiles before we add one
        Profiles().api1_1_profiles_library_get()
        profilesBefore = len(json.loads(self.__client.last_response.data))

        #Make sure that there is no profile with the same name from previous test runs
        rawj=  json.loads(self.__client.last_response.data)
        listLen =len(json.loads(self.__client.last_response.data))

        lastProfile =  rawj[listLen-1]
        lastName = str(lastProfile.get('name'))

        inList = False
        for i, val in enumerate (rawj):
            if ( self.addedName ==  str (rawj[i].get('name')) or inList ):
                inList = True
                nameList = str (rawj[i].get('name')).split('_')
                suffix= int (nameList[1]) + 1
                self.addedName = nameList[0]+ '_' + str(suffix)

        LOG.info ("added name " +  self.addedName)

        #add a profile
        LOG.info('Adding a profile named= {0}'.format(self.addedName))
        Profiles().api1_1_profiles_library_identifier_put(self.addedName,body=self.addedContents)
        resp= self.__client.last_response
        assert_equal(200,resp.status)

        #Get the number of profiles after we added one
        Profiles().api1_1_profiles_library_get()
        profilesAfter = len(json.loads(self.__client.last_response.data))
        resp= self.__client.last_response
        assert_equal(200,resp.status, message=resp.reason)

        #Validate that the profile has been added
        assert_equal(profilesAfter,profilesBefore+1)

        #Validate the content is as expected
        rawj=  json.loads(self.__client.last_response.data)
        listLen =len(json.loads(self.__client.last_response.data))
        readDict= rawj[listLen-1]
        readName= readDict.get('name')
        readContents  = readDict.get('contents')
        assert_equal(readName,self.addedName)
        assert_equal(readContents,self.addedContents)


    @test(groups=['profiles_library_identifier'], depends_on_groups=['profile_library_put'])
    def test_profiles_library_identifier_get(self):
        """ Testing GET:/library/:id"""

        Profiles().api1_1_profiles_library_identifier_get(self.addedName)
        readDict=  json.loads(self.__client.last_response.data)
        readContents  = readDict.get('contents')
        LOG.info('Reading the profile that was added,  {0}'.format(self.addedName))
        assert_equal(readContents,self.addedContents)

    @test(groups=['profiles_library_identifier_negative'], depends_on_groups=['profile_library_put'])
    def test_profiles_library_identifier_negative_get(self):
        """ Negative Testing GET:/library/:id"""
        try:
            Profiles().api1_1_profiles_library_identifier_get('wrongProfileName')
        except Exception,e:
           assert_equal(404,e.status, message = 'hello')




