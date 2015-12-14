from modules.urls import urls
from logger import Log

LOG = Log(__name__)

class Lookups(object):
    def __init__(self):
        self.__urls = urls()

    def get_lookups(self,uid=None,query=None):
        url = ''
        if uid is None and query is not None:
            url = '?q={0}'.format(query)
        return self.__send(uuid=uid,suffix=url)
    
    def post_lookups(self, lookup):
        return self.__send(attr='post',data=lookup)

    def patch_lookups(self, uid, lookup):
        return self.__send(uuid=uid,attr='patch',data=lookup)

    def delete_lookups(self, uid):
        return self.__send(uuid=uid,attr='delete')

    def __send(self,uuid=None,suffix=None,data=None,attr='get'):
        kwargs = {}
        path = '/lookups'
        if uuid is not None:
            path = '{0}/{1}'.format(path,uuid)
        if suffix is not None:
            path = '{0}/{1}'.format(path,suffix)
        kwargs['data'] = data
        rsp = getattr(self.__urls,attr)(path,**kwargs)
        return rsp

