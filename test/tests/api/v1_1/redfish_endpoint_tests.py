from config.api1_1_config import *
from config.settings import *
from modules.logger import Log
from modules.amqp import AMQPWorker
from modules.worker import WorkerThread, WorkerTasks
from on_http_api1_1 import NodesApi as Nodes
from on_http_api1_1 import rest
from on_http_api1_1 import PollersApi as Pollers
from on_http_api1_1 import WorkflowApi
from workflows_tests import WorkflowsTests as Workflows
from datetime import datetime
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_false
from proboscis.asserts import assert_raises
from proboscis.asserts import assert_true
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_is_not_none
from proboscis.asserts import fail
from proboscis import SkipTest
from proboscis import test
from proboscis import after_class
from proboscis import before_class
from json import loads

LOG = Log(__name__)

URI = defaults.get('RACKHD_REDFISH_URL', None)
ENABLED = True
if URI == None:
    ENABLED = False
IS_EMC = defaults.get('RACKHD_REDFISH_EMC_OEM', False)

ID_LED_GRAPH_LIST = [
    {
        'friendlyName': 'LED Lit',
        'injectableName': 'Graph.Set.IndentifyLED.On',
        'options': { 'led-on': { 'obmServiceName': 'redfish-obm-service' } },
        'tasks': [
            {
                'label': 'led-on',
                'taskName': 'Task.Obm.Node.IdentifyOn'
            }
        ]
    },
    {
        'friendlyName': 'Led Blinking',
        'injectableName': 'Graph.Set.IndentifyLED.Blink',
        'options': { 'led-blink': { 'obmServiceName': 'redfish-obm-service' } },
        'tasks': [
            {
                'label': 'led-blink',
                'taskName': 'Task.Obm.Node.IdentifyBlink'
            }
        ]
    },
    {
        'friendlyName': 'Led Off',
        'injectableName': 'Graph.Set.IndentifyLED.Off',
        'options': { 'led-off': { 'obmServiceName': 'redfish-obm-service' } },
        'tasks': [
            {
                'label': 'led-blink',
                'taskName': 'Task.Obm.Node.IdentifyOff'
            }
        ]
    }
]

def next_element(type, list):
    for item in list:
        if item['Type'] == type:
            return list.pop(list.index(item))

@test(groups=['redfish-endpoint.v1.1.tests'])
class RedfishEndpointTests(object):
    
    def __init__(self):
        self.__client = config.api_client
        self.__nodes = []
        self.__endpoints = []
        self.__system_name = 'newSystem'
            
    def __get_data(self):
        return loads(self.__client.last_response.data)
    
    def __post_unbound_workflow(self, graph_name, body):
        workflow = Workflows()
        workflow.post_unbound_workflow(graph_name, data=body)
        
    def __post_node_workflow(self, nodes, graph_name, body, tasks=[], callback=None):
        workflow = Workflows()
        workflow.post_workflows(graph_name, nodes=nodes, tasks=tasks, data=body, callback=callback)
    
    def __get_enclosure_ids(self):
        ids = []
        Nodes().nodes_get()
        nodes = self.__get_data()
        for node in nodes:
            if node.get('type') == 'enclosure':
                for obm in node.get('obmSettings', []):
                    if 'redfish-obm-service' == obm.get('service'):
                        ids.append(node.get('id'))
        return ids 
    
    @before_class(always_run=True)
    def setup(self):
        for graph in ID_LED_GRAPH_LIST:
            name = graph.get('injectableName')
            try:
                WorkflowApi().workflows_library_injectable_name_get(name)
            except rest.ApiException as e:
                if e.status == 404:
                    LOG.info('Adding graph definition \"{0}\"'.format(name))
                    WorkflowApi().workflows_put(body=graph)
        if IS_EMC:
            def callback(body, message):
                message.ack()
                for node in self.__get_enclosure_ids():
                    Nodes().nodes_identifier_workflows_active_get(node)
                    if self.__client.last_response.status == 204:
                        for task in tasks:
                            if task.id == node:
                                task.worker.stop()
                                task.running = False
            for id in self.__get_enclosure_ids():
                tasks = []
                body = {
                    'options': {
                        'defaults': {
                            'action': 'destroy',
                            'name': self.__system_name
                        }
                    }    
                }
                try:
                    self.__post_node_workflow([id], 'Graph.Emc.Compose.System', body, tasks=tasks, callback=callback)
                except rest.ApiException as e:
                    LOG.warning(e)

        
    @after_class(always_run=True)
    def teardown(self):
        for node in self.__nodes:
            id = node.get('id')
            assert_is_not_none(id)
            try:
                Pollers().nodes_identifier_pollers_get(id)
                pollers = self.__get_data()
                for p in pollers:
                    Pollers().pollers_identifier_delete(p.get('id'))
                Nodes().nodes_identifier_delete(id)
            except rest.ApiException as e:
                LOG.warning(e)
                     
    @test(enabled=ENABLED, \
        groups=['redfish-discovery.v1.1.test'])    
    def redfish_discovery_test(self):
        """ Testing Redfish Service Discovery """
        user, passwd = get_cred('redfish')
        assert_is_not_none(user)
        assert_is_not_none(passwd)
        body = {
            'options': {
                'defaults': {
                    'username': user,
                    'password': passwd,
                    'uri': URI
                }
            }
        }
            
        if IS_EMC:
            body['options']['when-catalog-emc'] = { 'autoCatalogEmc': 'true' }
            body['options']['when-pollers-emc'] = { 'autoCreatePollerEmc': 'true' }
            
        self.__post_unbound_workflow('Graph.Redfish.Discovery', body)
        Nodes().nodes_get()
        nodes = self.__get_data()
        
        settings = []
        for node in nodes:
            if node.get('type') == 'enclosure':
                for obm in node.get('obmSettings', []):
                    if obm.get('service') == 'redfish-obm-service':
                        self.__nodes.append(node)
                        config = obm.get('config')
                        assert_equal(URI, config.get('uri'), \
                            message = "Unexpected Redfish URI")
        assert_not_equal(len(self.__nodes), 0, message='Missing Redfish Enclosures')
        
    @test(enabled=ENABLED, \
        groups=['redfish-pollers.v1.1.test'], \
        depends_on_groups=['redfish-discovery.v1.1.test'])    
    def redfish_pollers_test(self):
        """ Testing Redfish Pollers """
        for node in self.__nodes:
            id = node.get('id')
            assert_is_not_none(id)
            Pollers().nodes_identifier_pollers_get(id)
            pollers = self.__get_data()
            assert_not_equal(len(pollers), 0, message='Unpexpected poller length')
            name = []
            for p in pollers:
                if p.get('name') == 'Pollers.Redfish':
                    name.append(p)
            assert_equal(len(pollers), len(name), \
                message='Unexpected pollers found in Redfish enclosure')
     
    @test(enabled=ENABLED, \
        groups=['redfish-indicator-led.v1.1.test'], \
        depends_on_groups=['redfish-discovery.v1.1.test'])    
    def redfish_indicator_led_test(self):
        """ Testing Redfish Chassis IndicatorLED Control """
        node_ids = self.__get_enclosure_ids()
        for graph in ID_LED_GRAPH_LIST:
            name = graph.get('injectableName')
            self.__post_node_workflow(node_ids, name, {})

    @test(enabled=IS_EMC, \
        groups=['redfish-emc-catalogs.v1.1.test'], \
        depends_on_groups=['redfish-discovery.v1.1.test'])    
    def redfish_emc_catalogs_test(self):
        """ Testing EMC Redfish Service Catalog """
        for node in self.__nodes:
            id = node.get('id')
            assert_is_not_none(id)
            Nodes().nodes_identifier_catalogs_get(id)
            catalog = self.__get_data()
            assert_not_equal(len(catalog), 0, message='EMC Redfish Catalog size failure')
            for data in catalog:
                assert_not_equal(len(data), 0, message='Unexpected EMC Catalog data size')
           
    @test(enabled=IS_EMC, \
        groups=['redfish-emc-compose.v1.1.test'], \
        depends_on_groups=['redfish-emc-catalogs.v1.1.test'])    
    def redfish_emc_compose_test(self):
        """ Testing EMC Redfish Compose Workflow """
        for node in self.__nodes:
            elements = []
            id = node.get('id')
            assert_is_not_none(id)
            Nodes().nodes_identifier_catalogs_get(id)
            catalog = self.__get_data()
            assert_not_equal(len(catalog), 0, message='EMC Redfish Catalog size failure')
            
            self.__endpoints = []
            self.__endpoints.append('ComputeElement{0}' \
                .format(next_element('ComputeElement', catalog[0].get('data')).get('Id')))
            self.__endpoints.append('StorageElement{0}' \
                .format(next_element('StorageElement', catalog[0].get('data')).get('Id')))
            self.__endpoints.append('StorageElement{0}' \
                .format(next_element('StorageElement', catalog[0].get('data')).get('Id')))
            body = {
                'options': {
                    'defaults': {
                        'endpoints': self.__endpoints,
                        'name': self.__system_name,
                        'action': 'compose'
                    }
                }    
            }
            self.__post_node_workflow([id], 'Graph.Emc.Compose.System', body)
        Nodes().nodes_get()
        nodes = self.__get_data() 
        for node in nodes:
            if self.__system_name in node.get('identifiers', []):
                for relation in node.get('relations', []):
                    if relation.get('relationType') == 'elementEndpoints':
                        assert_equal(sorted(relation.get('targets', [])), sorted(self.__endpoints), \
                            message='failure composed system endpoints')
                        return
        # test failure if we get here
        fail('Failed to find composed system')
        
    @test(enabled=IS_EMC, \
        groups=['redfish-emc-recompose.v1.1.test'], \
        depends_on_groups=['redfish-emc-compose.v1.1.test'])    
    def redfish_emc_recompose_test(self):
        """ Testing EMC Redfish Recompose Workflow """
        for node in self.__nodes:
            elements = []
            id = node.get('id')
            assert_is_not_none(id)
            Nodes().nodes_identifier_catalogs_get(id)
            catalog = self.__get_data()
            assert_not_equal(len(catalog), 0, message='EMC Redfish Catalog size failure')
            
            for endpoint in self.__endpoints:
                if 'StorageElement' in endpoint:
                    index = self.__endpoints.index(endpoint)
                    self.__endpoints.pop(index)
                    break
            body = {
                'options': {
                    'defaults': {
                        'endpoints': self.__endpoints,
                        'name': self.__system_name,
                        'action': 'recompose'
                    }
                }    
            }
            self.__post_node_workflow([id], 'Graph.Emc.Compose.System', body)
        Nodes().nodes_get()
        nodes = self.__get_data() 
        for node in nodes:
            if self.__system_name in node.get('identifiers', []):
                for relation in node.get('relations', []):
                    if relation.get('relationType') == 'elementEndpoints':
                        assert_equal(sorted(relation.get('targets', [])), sorted(self.__endpoints), \
                            message='failure recomposed system endpoints')
                        return
        # test failure if we get here
        fail('Failed to find recomposed system')
        
    @test(enabled=IS_EMC, groups=['redfish-emc-destroy.v1.1.test'], \
        depends_on_groups=['redfish-emc-recompose.v1.1.test'])    
    def redfish_emc_destroy_test(self):
        """ Testing EMC Redfish Destroy Workflow """
        for node in self.__nodes:
            id = node.get('id')
            assert_is_not_none(id)
            body = {
                'options': {
                    'defaults': {
                        'action': 'destroy',
                        'name': self.__system_name
                    }
                }    
            }
            self.__post_node_workflow([id], 'Graph.Emc.Compose.System', body)
        Nodes().nodes_get()
        nodes = self.__get_data() 
        for node in nodes:
            if node.get('type') == 'compute':
                if self.__system_name in node.get('identifiers'):
                    fail('failure deleting composed system')


        