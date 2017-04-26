from __future__ import print_function
import os
import os.path
import re
from docker import Client


class _VCheckedClient(Client):
    _REQUIRED_DOCKER_VERSION = '1.12'

    def __init__(self, *args, **kwargs):
        super(_VCheckedClient, self).__init__(*args, **kwargs)
        client_vinfo = self.version()
        assert '1.12' in client_vinfo['Version'], \
            'Need a 1.12ish docker version, found {0}'.format(client_vinfo['Version'])


class AMQPOnDemand(object):
    _RABBITMQ_REPO_NAME = 'rabbitmq'
    _RABBITMQ_TAG = 'management'
    _RABBITMQ_IMAGE_NAME = '{0}:{1}'.format(_RABBITMQ_REPO_NAME, _RABBITMQ_TAG)

    def __init__(self):
        self.__main_client = _VCheckedClient(timeout=600)

        # make a name that is unique by directory.
        base_name = "rabbitmq-for-{0}".format(os.getcwd())
        # make it docker-name safe (todo: this isn't complete yet)
        safe_name = re.sub(r'''\s|/''', '-', base_name)

        existing = self.__assure_running(safe_name)
        assert existing is not None, \
            'failed to find or create test rabbitmq server'

        self.__rabbit = existing

    def __assure_running(self, safe_name):
        running = False
        while not running:
            existing = self.__find_by_name(safe_name)
            if existing is None:
                self.__start_rabbitmq(safe_name)
            else:
                state = existing["State"]
                if state == 'running':
                    running = True
                elif state == 'exited':
                    response = self.__main_client.start(container=existing.get('Id'))
                    # todo: log
                    print(response)
                else:
                    raise Exception("state = {0}".format(state))
        return existing

    def __find_by_name(self, safe_name):
        containers = self.__main_client.containers(
            all=True, filters={'name': safe_name})
        if len(containers) == 0:
            return None
        assert len(containers) == 1, \
            'impossible-result: docker names are unique, but found multiple for {0} ({1}}'.format(
                safe_name, containers)
        # todo: log
        # print "containters"* 30
        # import pprint
        # pprint.pprint(containers[0]['Ports'])
        return containers[0]

    def __start_rabbitmq(self, safe_name):
        # Make sure we have the image...
        pull_output = self.__main_client.pull(
            self._RABBITMQ_REPO_NAME, tag=self._RABBITMQ_TAG, stream=True)

        # todo: log
        for line in pull_output:
            pass

        # todo: hashify or randomize port ids so more than one of these can
        #  run at once.
        host_config = self.__main_client.create_host_config(
            dns=[],
            port_bindings={
                4369: ('127.0.0.1',),
                5671: ('127.0.0.1',),
                5672: ('127.0.0.1',),
                15671: ('127.0.0.1',),
                15672: ('127.0.0.1',),
                25672: ('127.0.0.1',)
            })
        dockproc = self.__main_client.create_container(
            image=self._RABBITMQ_IMAGE_NAME, name=safe_name, tty=True,
            host_config=host_config)

        # todo: see if we need 'command="--insecure-registry=mubmle' as param to above.

        # response = self.__main_client.start(container=dockproc.get('Id'))
        self.__main_client.start(container=dockproc.get('Id'))
        # todo: log
        # print response
        return dockproc

    @property
    def host(self):
        return '127.0.0.1'

    @property
    def ssl_port(self):
        return self.__find_port_for(5672)

    @property
    def port(self):
        return self.__find_port_for(5671)

    def __find_port_for(self, base_port):
        for port in self.__rabbit['Ports']:
            # It MUST have a private port (what is bound inside the proc)
            # TODO: fix private-only actually MEANS private only!!!
            if port['PrivatePort'] == base_port:
                # It MAY have a public one, if it is mapped. Otherwise it
                # will be bound to the same as the private one.
                return port.get('PublicPort', base_port)

        return None
