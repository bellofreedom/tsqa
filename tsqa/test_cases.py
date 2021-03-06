'''
Some base test cases that do environment handling for you
'''
import logging

import tsqa.endpoint
import tsqa.environment
import tsqa.configs
import tsqa.utils
unittest = tsqa.utils.import_unittest()

import os

# Base environment case
class EnvironmentCase(unittest.TestCase):
    '''
    This class will get an environment (which is unique)
    '''
    # TODO: better naming??
    environment_factory = {'configure': None,
                           'env': None,
                           }

    def run(self, result=None):
        unittest.TestCase.run(self, result)
        self.__successful &= result.result.wasSuccessful()

    @classmethod
    def setUpClass(cls):
        # call parent constructor
        super(EnvironmentCase, cls).setUpClass()

        # get a logger
        cls.log = logging.getLogger(__name__)

        # get an environment
        cls.environment = cls.getEnv()
        # TODO: better... I dont think this output is captured in each test run
        logging.info('Environment prefix is {0}'.format(cls.environment.layout.prefix))

        cfg_dir = os.path.join(cls.environment.layout.prefix, 'etc', 'trafficserver')

        # create a bunch of config objects that people can access/modify
        # classes that override our default config naming
        config_classes = {'records.config': tsqa.configs.RecordsConfig}
        # create a mapping of config-name -> config-obj
        cls.configs = {}
        for name in os.listdir(cls.environment.layout.sysconfdir):
            path = os.path.join(cls.environment.layout.sysconfdir, name)
            if os.path.isfile(path):
                cls.configs[name] = config_classes.get(name, tsqa.configs.Config)(path)

        # call env setup, so people can change configs etc
        cls.setUpEnv(cls.environment)

        for _, cfg in cls.configs.iteritems():
            cfg.write()

        # start ATS
        cls.environment.start()

        # we assume the tests passed
        cls.__successful = True

    @classmethod
    def getEnv(cls):
        '''
        This function is responsible for returning an environment. The default
        is to build ATS and return a copy of an environment
        '''
        SOURCE_DIR = os.getenv('TSQA_SRC_DIR', '~/trafficserver')
        TMP_DIR = os.getenv('TSQA_TMP_DIR','/tmp/tsqa')
        ef = tsqa.environment.EnvironmentFactory(SOURCE_DIR, os.path.join(TMP_DIR, 'base_envs'))
        return ef.get_environment(cls.environment_factory['configure'], cls.environment_factory['env'])

    @classmethod
    def setUpEnv(cls, env):
        '''
        This funciton is responsible for setting up the environment for this fixture
        This includes everything pre-daemon start (configs, certs, etc.)
        '''
        pass

    @classmethod
    def tearDownClass(cls):
        if not cls.environment.running():
            raise Exception('ATS died during the test run')
        # stop ATS
        cls.environment.stop()

        # call parent destructor
        super(EnvironmentCase, cls).tearDownClass()
        # if the test was successful, tear down the env
        if cls.__successful:
            cls.environment.destroy()  # this will tear down any processes that we started

    # Some helpful properties
    @property
    def proxies(self):
        '''
        Return a dict of schema -> proxy. This is primarily used for requests
        '''
        # TODO: create a better dict by parsing the config-- to handle http/https ports in the string
        return {'http': 'http://127.0.0.1:{0}'.format(self.configs['records.config']['CONFIG']['proxy.config.http.server_ports'])}


class DynamicHTTPEndpointCase(unittest.TestCase):
    '''
    This class will set up a dynamic http endpoint that is local to this class
    '''
    @classmethod
    def setUpClass(cls, port=0):
        # get a logger
        cls.log = logging.getLogger(__name__)

        cls.http_endpoint = tsqa.endpoint.DynamicHTTPEndpoint(port=port)
        cls.http_endpoint.start()

        cls.http_endpoint.ready.wait()

        # create local requester object
        cls.track_requests = tsqa.endpoint.TrackingRequests(cls.http_endpoint)

        # Do this last, so we can get our stuff registered
        # call parent constructor
        super(DynamicHTTPEndpointCase, cls).setUpClass()

    def endpoint_url(self, path=''):
        '''
        Get the url for the local dynamic endpoint given a path
        '''
        if path and not path.startswith('/'):
            path = '/' + path
        return 'http://127.0.0.1:{0}{1}'.format(self.http_endpoint.address[1],
                                                path)

