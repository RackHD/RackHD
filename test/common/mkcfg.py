import jsonmerge
import jsonmerge.strategies
from singleton import Singleton
import argparse
import os
import sys
import time
import json

#pylint: disable=invalid-name

class mkcfgException(Exception):
    pass

class mkcfg(object):

    """
    Manages a RackHD test configuration

    # Singleton object creation:
    mkcfg()

    # Access the singleton
    cfg = mkcfg()

    # add a list of json configs
    cfg.add_from_file_list(json_config_file_list)

    # add a single json config
    cfg.add_from_file_list(json_config_file_list)

    # add a json config from dict
    cfg.add_from_dict(config_dict)

    # write out configuration
    cfg.generate()

    # retrieve the config as a dict
    cfg_dict = cfg.get()

    # retrieve the path to saved configuration
    cfg_dict = cfg.get_path()
    """

    # mkcfg is a singleton
    __metaclass__ = Singleton

    config_env = 'FIT_CONFIG'

    def __init__(self):
        self.config_path = os.environ.get(self.config_env, None)
        if self.config_path:
            # load up an existing configuration
            print "*** Reloading config file: " + self.config_path
            self.generated_config_path = self.config_path
            self.config_dict = self.__read_config(self.generated_config_path)
            self.config_dir = self.config_dict['cmd-args-list']['config']
            self.generated_dir = self.config_dir + '/generated'

    def config_is_loaded(self):
        return self.config_path is not None

    def config_exists(self, filename):
        return os.path.isfile(self.config_dir + '/' + filename)

    def create(self, config_dir='config'):
        if self.config_path:
            raise mkcfgException('creating configuration on top of existing object')
        # prepare for creation of new configuration
        self.generated_config_path = None
        self.config_dict = dict()
        self.config_dir = config_dir
        self.generated_dir = self.config_dir + '/generated'

    def add_from_file_list(self, json_config_list):
        """
        add a list of json configuration files
        :param json_config_list: file list
        :return: None
        """
        for json_config in json_config_list:
            self.add_from_file(json_config)

    def add_from_file(self, json_config, key=None):
        """
        add a single json configuration file
        :param json_config: json config file
        :return: None
        """
        config_dict = self.__read_config(self.config_dir + '/' + json_config)
        if key:
            if key in config_dict:
                config_dict = config_dict[key]
            else:
                raise mkcfgException('unknown key = ' + key)
        self.__merge(config_dict)

    def add_from_dict(self, add_dict):
        """
        merge a dictionary into config dict
        :param add_dict:
        :return:
        """
        self.__merge(add_dict)

    def generate(self):
        """
        generate a configuration file
        :return: None
        """
        self.generated_config_path = self.__write_config_file()
        os.environ[self.config_env] = self.generated_config_path
        print "*** Created config file: " + self.generated_config_path

    def get(self):
        """
        returns a rackhd test configuration as a dictionary
        :return:
        """
        return self.config_dict

    def get_path(self):
        """
        returns the path to the generated configuration file
        :return:
        """
        return self.generated_config_path

    def destroy(self):
        """
        destroys the existing configuration singleton object
        :return:
        """
        Singleton.purge(mkcfg)

    def __merge(self, json_blob):
        """
        json merge a json blob into config_dict
        :param json_blob:
        :return:
        """
        schema = {'mergeStrategy': 'objectMerge'}
        self.config_dict = jsonmerge.merge(self.config_dict, json_blob, schema)

    def __write_config_file(self, prepend=''):
        """
        write a json configuration file with a timestamped name
        :return:
        """
        timestr = prepend + time.strftime("%Y%m%d-%H%M%S")
        config_path = self.generated_dir + '/' + 'fit-config-' + timestr
        with open(config_path, 'w') as outf:
            json.dump(self.config_dict, outf, indent=4, sort_keys=True)
        return config_path

    @staticmethod
    def __read_config(json_config):
        """
        read a json configuration file
        :return:
        """
        try:
            with open(json_config, 'r') as file_handle:
                try:
                    return json.load(file_handle)
                except ValueError as value_e:
                    print value_e
                    return None
        except (OSError, IOError) as load_e:
            print load_e
            return None

    def dump(self):
        """
        print the config dictionary to stdout
        :return:
        """
        print json.dumps(self.config_dict, indent=4, sort_keys=True)


if __name__ == "__main__":

    def usage_docstring(prog_base):
        """
        {0}

        self test of mkcfg

        Options supported:
            -c <config>  : configuration directory
            -a <json config> : overlay file (merged first)
            <-a <json config> : overlay file (merged second)>
            <-a <json config> : overlay file (merged third)>
            ...
            The created configuration is written to stdout

        For example:
            test_config -c config -a rackhd_default.json -a credentials_default.json -a install_default.json
        """
        return usage_docstring.__doc__.format(prog_base)

    PROG_NAME = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser()
    parser.add_argument('-c')
    parser.add_argument('-a', action='append')
    args = parser.parse_args()
    config_dir_arg = args.c
    json_config_files_arg = args.a

    # we require config_dir and json_config_files
    if not config_dir_arg or not json_config_files_arg:
        print usage_docstring(PROG_NAME)
        exit(1)

    # specify a sample argument list
    ARGS_LIST = {
        "cmd-args-list": {
            "v": "v_value",
            "config": "config_value",
            "stack": "stack_value",
            "ora": "ora_value",
            "bmc": "bmc_value",
            "sku": "sku_value",
            "obmmac": "obmmac_value",
            "nodeid": "nodeid_value",
            "http": 8080,
            "https": 443
        }
    }

    # Test config creation
    cfg = mkcfg()

    cfg.create()
    cfg.add_from_file_list(json_config_files_arg)
    cfg.add_from_dict(ARGS_LIST)
    cfg.dump()
    cfg.generate()

    # Dump out the configuration path.  We should be able to access with cfg object
    print "path = " + mkcfg().get_path()

    # Get config singleton object and compare dictionaries
    cfg2 = mkcfg()
    if cfg2.config_dict != cfg.config_dict:
        print 'singleton is broken'
        exit(1)

    # throw away configuration
    cfg.destroy()

    # reload from FIT_CONFIG which should be in the environment from original mkcfg
    cfg = mkcfg()
    if cfg.config_is_loaded():
        cfg.dump()
    else:
        print 'we should already have configuration'
        exit(1)
    print "path = " + mkcfg().get_path()
    cfg.dump()

    exit(0)

