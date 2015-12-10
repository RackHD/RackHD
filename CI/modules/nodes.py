from modules.urls import urls
from logger import Log

LOG = Log(__name__)

class Nodes(object):
    def __init__(self):
        self.__urls = urls()

    def get_nodes(self,uid=None):
        return self.__send(uuid=uid)

    def post_node(self, uid):
        return self.__send(uuid=uid,attr='post')

    def patch_node(self, uid, node):
        return self.__send(uuid=uid,attr='patch',data=node)

    def delete_node(self, uud):
        return self.__send(uuid=uid,attr='delete')

    def get_node_catalog(self, uid,source=''):
        return self.__send(uuid=uid,suffix='{0}/{1}'.format('catalogs',source))

    def get_node_obm(self, uid):
        return self.__send(uuid=uid,suffix='obm')

    def get_node_pollers(self, uid):
        return self.__send(uuid=uid,suffix='pollers')

    def __send(self,uuid=None,suffix=None,data=None,attr='get'):
        kwargs = {}
        path = '/nodes'
        if uuid is not None:
            path = '{0}/{1}'.format(path,uuid)
            if suffix is not None:
                path = '{0}/{1}'.format(path,suffix)
        kwargs['data'] = data
        rsp = getattr(self.__urls,attr)(path,**kwargs)
        return rsp

