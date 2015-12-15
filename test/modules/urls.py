from config.settings import *
from logger import Log
import requests

LOG = Log(__name__)

"""
Class to abstract HTTP request functionality
:param verify: optional validate SSL certificate 
:param json: optional always return formated JSON data
:param headers: optional header object
"""
class urls(object):
    def __init__(self, **kwargs):
        self.sslVerify = kwargs.get('verify',False)
        self.headers = kwargs.get('headers', { 'Content-Type':'application/json' })
        self.pfx = 'https' if self.sslVerify else 'http'
        self.url = '{0}://{1}:{2}/{3}'.format(self.pfx,HOST_IP,HOST_PORT,'api/{0}'.format(API_VERSION))
        self.json = kwargs.get('json', False)

    def get(self, url, data=None):
        return self.__send(url,'get')

    def post(self, url, data=None):
        return self.__send(url,'post',data)
    
    def delete(self, url, data=None):
        return self.__send(url,'delete')

    def put(self, url, data=None):
        return self.__send(url,'put',data)

    def patch(self, url, data=None):
        return self.__send(url,'patch',data)

    def __send(self,url,attr,data=None):
        resp = None
        url = '{0}{1}'.format(self.url, url)
        LOG.debug('{0}:{1}'.format(attr,url))

        if data is not None:
            resp = getattr(requests,attr)(url,data,headers=self.headers)
        else:
            resp = getattr(requests,attr)(url,headers=self.headers)
        if resp is None:
            raise TypeError('Unexpected HTTP request response type')
        return self.__format(attr,resp)

    def __format(self, attr, body):
        if self.json:
            return body.json()
        return body

